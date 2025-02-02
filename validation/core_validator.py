import asyncio
import re
import threading
from collections import defaultdict, deque
from typing import Dict, Tuple
from typing import List
from typing import Optional
from typing import Set
from fastapi.responses import JSONResponse
import httpx
from pydantic import BaseModel
import time
from core import Task
from core import TASK_TO_MAX_CAPACITY
import bittensor as bt
from validation.synthetic_data.synthetic_generations import SyntheticDataManager
from validation.proxy.utils import query_utils
from core import bittensor_overrides as bto
from config import configuration
from config.validator_config import config as validator_config
from models import base_models, synapses, utility_models
from validation.proxy import validation_utils

from validation.scoring.main import Scorer
from validation.uid_manager import UidManager
from validation.weight_setting.main import WeightSetter
from validation.db import post_stats
from validation.db.db_management import db_manager
from core import constants as core_cst

PROXY_VERSION = "4.2.2"
# Change this to not be hardcoded, once the orchestrator supports is
ORCHESTRATOR_VERSION = "0.1.0"

_PASCAL_SEP_REGEXP = re.compile("(.)([A-Z][a-z]+)")
_UPPER_FOLLOWING_REGEXP = re.compile("([a-z0-9])([A-Z])")
MAX_PERIODS_TO_LOOK_FOR_SCORE = 16


def _health_check(base_url: str):
    try:
        response = httpx.get(base_url)
        return response.status_code == 200
    except httpx.RequestError:
        print(f"Health check failed for now - can't connect to {base_url}.")
        return False


def _connect_to_external_server(hotkey_name: str, external_server_url: str) -> str:
    servers = {
        core_cst.EXTERNAL_SERVER_ADDRESS_PARAM: external_server_url,
    }

    # Check each server
    for name, url in servers.items():
        if url is None:
            raise Exception(f"{hotkey_name}.{name.upper()} not set in the config")

        retry_interval = 2
        while True:
            connected = _health_check(url)
            if connected:
                bt.logging.info(f"Health check successful - connected to {name} at {url}.")
                break
            else:
                bt.logging.info(
                    f"{name} at url {url} not reachable just yet- it's probably still starting. Sleeping for {retry_interval} second(s) before retrying."
                )
                time.sleep(retry_interval)
                retry_interval += 5
                if retry_interval > 15:
                    retry_interval = 15


class CoreValidator:
    def __init__(self) -> None:
        self.config = self.prepare_config_and_logging()
        self.subtensor = bt.subtensor(config=self.config)
        self.wallet = bt.wallet(config=self.config)
        self.keypair = self.wallet.hotkey
        self.dendrite = bto.dendrite(wallet=self.wallet)
        self.metagraph: bt.metagraph = self.subtensor.metagraph(netuid=self.config.netuid, lite=True)
        self.netuid: int = self.config.netuid if self.config.netuid is not None else 19
        self.task_weights = self._get_task_weights()

        self.is_testnet = validator_config.subtensor_network == "test" or self.netuid != 19

        self.public_hotkey_address = self.keypair.ss58_address

        _my_stake = self.metagraph.S[self.metagraph.hotkeys.index(self.public_hotkey_address)]
        self.validator_uid = self.metagraph.hotkeys.index(self.public_hotkey_address)
        self._my_prop_of_stake = (_my_stake / sum(self.metagraph.S)).item()

        if self.is_testnet:
            self._my_prop_of_stake = 1.0

        _connect_to_external_server(validator_config.hotkey_name, validator_config.external_server_url)

        # Make the above class variables instead

        bt.logging(debug=True)

        self.uids: list[int] = []
        self.axon_indexes: list[int] = []
        self.incentives: list[float] = []

        self.uid_to_uid_info: Dict[int, utility_models.UIDinfo] = {}
        self.previous_uid_infos: deque[List[utility_models.UIDinfo]] = deque([], maxlen=MAX_PERIODS_TO_LOOK_FOR_SCORE)

        self.low_incentive_uids: Set[int] = set()

        self.capacities_for_tasks: Dict[Task, Dict[int, float]] = defaultdict(lambda: {})  # task -> uid -> capacity

        self.threading_lock = threading.Lock()

        self.task_id_to_work: Dict[str, float] = {}

        self.results_store: Dict[str, utility_models.QueryResult] = {}

        self.scorer = Scorer(validator_hotkey=self.keypair.ss58_address, testnet=self.is_testnet, keypair=self.keypair)
        self.weight_setter = WeightSetter(subtensor=self.subtensor, config=self.config)
        self.synthetic_data_manager = SyntheticDataManager(self.validator_uid)
        self.uid_manager = None

    def _get_task_weights(self) -> Dict[Task, float]:
        weights = {
            #
            Task.chat_llama_3_1_8b: 0.15,
            Task.chat_llama_3_1_70b: 0.20,
            #
            Task.proteus_text_to_image: 0.10,
            Task.flux_schnell_text_to_image: 0.15,
            Task.dreamshaper_text_to_image: 0.05,
            #
            Task.proteus_image_to_image: 0.05,
            Task.flux_schnell_image_to_image: 0.05,
            Task.dreamshaper_image_to_image: 0.05,
            #
            Task.jugger_inpainting: 0.05,
            Task.avatar: 0.15,
        }

        db_manager.task_weights = weights
        return weights

    async def _post_and_correct_capacities(self) -> None:
        self._correct_for_max_capacities()
        await self._post_miner_capacities_to_tauvision()
        self._correct_capacities_for_my_stake()

    def _correct_capacities_for_my_stake(self) -> None:
        my_proportion_of_stake = self._my_prop_of_stake

        for task in Task:
            capacities = self.capacities_for_tasks[task]
            for uid, capacities_for_uid in capacities.items():
                capacities[uid] = capacities_for_uid * my_proportion_of_stake

    def _correct_for_max_capacities(self) -> None:
        for task in Task:
            capacities = self.capacities_for_tasks[task]
            max_capacity = TASK_TO_MAX_CAPACITY[task]
            for uid, capacity in capacities.items():
                if capacity < 1:
                    self.capacities_for_tasks[task][uid] = 0
                self.capacities_for_tasks[task][uid] = min(capacity, max_capacity)

    def prepare_config_and_logging(self) -> bt.config:
        base_config = configuration.get_validator_cli_config()

        bt.logging(config=base_config, logging_dir=base_config.full_path)
        return base_config

    def start_continuous_tasks(self):
        self.score_task = asyncio.create_task(self.run_vali())
        self.score_task.add_done_callback(validation_utils.log_task_exception)

    async def fetch_available_capacities_for_each_axon(self) -> None:
        uid_to_query_task = {}

        for uid in self.uid_to_uid_info.keys():
            task = asyncio.create_task(
                query_utils.query_individual_axon(
                    synapse=synapses.Capacity(),
                    dendrite=self.dendrite,
                    axon=self.uid_to_uid_info[uid].axon,
                    axon_uid=uid,
                    deserialize=True,
                    log_requests_and_responses=False,
                )
            )

            uid_to_query_task[uid] = task

        responses_and_response_times: List[
            Tuple[Optional[Dict[Task, base_models.VolumeForTask]], float]
        ] = await asyncio.gather(*uid_to_query_task.values())

        uids = uid_to_query_task.keys()
        all_capacities = [i[0] for i in responses_and_response_times]

        bt.logging.info(f"Got capacities from {len([i for i in all_capacities if i is not None])} axons!")
        with self.threading_lock:
            self.capacities_for_tasks = defaultdict(lambda: {})
            for uid, capacities in zip(uids, all_capacities):
                if capacities is None:
                    continue

                allowed_tasks = set([task for task in Task])
                for task, volume in capacities.items():
                    # This is to stop people claiming tasks that don't exist
                    if task not in allowed_tasks:
                        continue
                    if uid not in self.capacities_for_tasks[task]:
                        self.capacities_for_tasks[task][uid] = float(volume.volume)
            await self._post_and_correct_capacities()

        bt.logging.info("Done fetching available tasks!")

    async def resync_metagraph(self):
        """
        Resyncs the metagraph and updates the hotkeys and moving averages based on the new metagraph.
        This really needs to work in a separate runtime environment, or can query an api directly as a first try
        """
        bt.logging.info("Resyncing the metagraph!")
        await asyncio.to_thread(self.metagraph.sync, subtensor=self.subtensor, lite=True)

        bt.logging.info("Got the capacities, now storing the info....")
        incentives_tensor, axon_indexes_tensor = self.metagraph.incentive.sort(descending=True)

        with self.threading_lock:
            self.uid_to_uid_info = {}
            self.uids: List[int] = self.metagraph.uids.tolist()
            self.axon_indexes = axon_indexes_tensor.tolist()
            self.incentives = incentives_tensor.tolist()
            hotkeys: List[str] = self.metagraph.hotkeys  # noqa: F841
            axons = self.metagraph.axons

            for i in self.axon_indexes:
                uid = self.uids[i]
                self.uid_to_uid_info[uid] = utility_models.UIDinfo(
                    uid=uid,
                    axon=axons[i],
                    hotkey=hotkeys[i],
                )

        bt.logging.info("Finished extraction - now to fetch the available capacities for each axon")
        await self.fetch_available_capacities_for_each_axon()

        return

    async def _post_miner_capacities_to_tauvision(self) -> None:
        data_to_post = []
        for task in self.capacities_for_tasks:
            for uid, volume in self.capacities_for_tasks[task].items():
                hotkey = self.uid_to_uid_info[uid].hotkey
                data_to_post.append(
                    post_stats.MinerCapacitiesPostObject(
                        validator_hotkey=self.public_hotkey_address, miner_hotkey=hotkey, task=task, volume=volume
                    )
                )
        post_data = post_stats.MinerCapacitiesPostBody(data=data_to_post)
        await post_stats.post_to_tauvision(
            data_to_post=post_data.dump(),
            keypair=self.keypair,
            data_type_to_post=post_stats.DataTypeToPost.MINER_CAPACITIES,
        )

    def _post_uid_records_to_tauvision(self) -> None:
        data_to_post = []
        for task in self.uid_manager.uid_records_for_tasks:
            for record in self.uid_manager.uid_records_for_tasks[task].values():
                data_to_post.append(
                    post_stats.UidRecordPostObject(
                        miner_hotkey=record.hotkey,
                        validator_hotkey=self.public_hotkey_address,
                        axon_uid=record.axon_uid,
                        period_score=record.period_score,
                        declared_volume=record.declared_volume,
                        consumed_volume=record.consumed_volume,
                        requests_429=record.requests_429,
                        requests_500=record.requests_500,
                        total_requests_made=record.total_requests_made,
                        task=task,
                    )
                )

        post_data = post_stats.UidRecordsPostBody(data=data_to_post)
        asyncio.create_task(
            post_stats.post_to_tauvision(
                data_to_post=post_data.dump(),
                keypair=self.keypair,
                data_type_to_post=post_stats.DataTypeToPost.UID_RECORD,
            )
        )

    def _post_uid_records_to_tauvision(self) -> None:
        data_to_post = []
        for task in self.uid_manager.uid_records_for_tasks:
            for record in self.uid_manager.uid_records_for_tasks[task].values():
                data_to_post.append(
                    post_stats.UidRecordPostObject(
                        miner_hotkey=record.hotkey,
                        validator_hotkey=self.public_hotkey_address,
                        axon_uid=record.axon_uid,
                        period_score=record.period_score,
                        declared_volume=record.declared_volume,
                        consumed_volume=record.consumed_volume,
                        requests_429=record.requests_429,
                        requests_500=record.requests_500,
                        total_requests_made=record.total_requests_made,
                        task=task,
                    )
                )

        post_data = post_stats.UidRecordsPostBody(data=data_to_post)
        asyncio.create_task(
            post_stats.post_to_tauvision(
                data_to_post=post_data.dump(),
                keypair=self.keypair,
                data_type_to_post=post_stats.DataTypeToPost.UID_RECORD,
            )
        )

    async def run_vali(self) -> None:
        await db_manager.delete_reward_data_after_update()
        iteration = 1
        while True:
            await post_stats.post_to_tauvision(
                data_to_post={
                    "versions": PROXY_VERSION + ":" + ORCHESTRATOR_VERSION,
                    "validator_hotkey": self.public_hotkey_address,
                },
                keypair=self.keypair,
                data_type_to_post=post_stats.DataTypeToPost.VALIDATOR_INFO,
            )

            await db_manager.delete_data_older_than_date(minutes=60 * 24)
            await db_manager.delete_tasks_older_than_date(minutes=120)

            # Wait for initial syncing of metagraph
            await self.resync_metagraph()
            self.scorer.start_scoring_results_if_not_already()

            bt.logging.info("🚀 Starting to score stuff, metagraph is synced...")
            self.uid_manager = UidManager(
                self.capacities_for_tasks,
                dendrite=self.dendrite,
                uid_to_uid_info=self.uid_to_uid_info,
                validator_hotkey=self.keypair.ss58_address,
                synthetic_data_manager=self.synthetic_data_manager,
                is_testnet=self.is_testnet,
            )

            await self.uid_manager.start_synthetic_scoring()
            await self.uid_manager.collect_synthetic_scoring_results()
            self.uid_manager.calculate_period_scores_for_uids()
            self._post_uid_records_to_tauvision()
            await self.uid_manager.store_period_scores()

            bt.logging.info(f"Finished scoring for iteration: {iteration}. Now settings weights")
            iteration += 1

            await self.weight_setter.start_weight_setting_process(
                self.metagraph,
                self.wallet,
                self.config.netuid,
                self.capacities_for_tasks,
                self.uid_to_uid_info,
                self.task_weights,
            )

            await asyncio.sleep(60)

    async def make_organic_query(
        self, task: Task, stream: bool, outgoing_model: BaseModel, synapse: bt.Synapse
    ) -> JSONResponse:
        if self.uid_manager is None:
            return JSONResponse(status_code=500, content={"message": "Server booting, one sec"})

        return await self.uid_manager.make_organic_query(
            task=task, synapse=synapse, stream=stream, outgoing_model=outgoing_model
        )


core_validator = CoreValidator()
