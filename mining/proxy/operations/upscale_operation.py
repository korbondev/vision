from typing import Tuple, TypeVar

import bittensor as bt
from core.bittensor_overrides import synapse as bto_synapse

bt.synapse = bto_synapse

from mining.proxy import core_miner
from mining.proxy.operations import abstract_operation
from models import base_models, synapses
from operation_logic import upscale_logic

operation_name = "UpscaleOperation"

T = TypeVar("T", bound=bt.Synapse)


class UpscaleOperation(abstract_operation.Operation):
    @staticmethod
    async def forward(synapse: synapses.Upscale) -> synapses.Upscale:
        output = await upscale_logic.upscale_logic(base_models.UpscaleIncoming(**synapse.model_dump()))

        synapse.image = None

        output_dict = output.model_dump()
        for field in output_dict:
            setattr(synapse, field, output_dict[field])
        return synapse

    @staticmethod
    async def blacklist(synapse: synapses.Upscale) -> Tuple[bool, str]:
        return core_miner.base_blacklist(synapse)

    @staticmethod
    async def priority(synapse: synapses.Upscale) -> float:
        return core_miner.base_priority(synapse)
