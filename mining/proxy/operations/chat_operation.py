from typing import Tuple, TypeVar, AsyncIterator

import bittensor as bt

from core import tasks
from mining.proxy import core_miner
from mining.proxy.operations import abstract_operation
from models import base_models, synapses
from operation_logic import chat_logic
from starlette.types import Send
from functools import partial
from models import utility_models
from config.miner_config import config as miner_config

operation_name = "ChatOperation"

T = TypeVar("T", bound=bt.Synapse)


async def _send_text(text_generator: AsyncIterator[bytes], send: Send):
    try:
        async for text in text_generator:
            await send(
                {
                    "type": "http.response.body",
                    "body": text,
                    "more_body": True,
                }
            )
        await send(
            {
                "type": "http.response.body",
                "body": b"",
                "more_body": False,
            }
        )

    except Exception as e:
        bt.logging.error(e)


class ChatOperation(abstract_operation.Operation):
    @staticmethod
    @abstract_operation.enforce_concurrency_limits
    async def forward(synapse: synapses.Chat) -> synapses.Chat:
        if synapse.model == utility_models.ChatModels.llama_3_1_8b.value:
            url = miner_config.llama_3_1_8b_text_worker_url
        elif synapse.model == utility_models.ChatModels.llama_3_1_70b.value:
            url = miner_config.llama_3_1_70b_text_worker_url
        else:
            raise NotImplementedError(f"Model {synapse.model} not implemented for chat operation")
        task = tasks.get_task_from_synapse(synapse)
        text_generator = await chat_logic.chat_logic(base_models.ChatIncoming(**synapse.dict()), url, task)

        text_streamer = partial(_send_text, text_generator)
        return synapse.create_streaming_response(text_streamer)

    @staticmethod
    async def blacklist(synapse: synapses.Chat) -> Tuple[bool, str]:
        return core_miner.base_blacklist(synapse)

    @staticmethod
    async def priority(synapse: synapses.Chat) -> float:
        return core_miner.base_priority(synapse)
