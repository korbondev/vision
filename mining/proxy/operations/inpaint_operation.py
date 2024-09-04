from typing import Tuple, TypeVar

import bittensor as bt
from core.bittensor_overrides import synapse as bto_synapse

bt.synapse = bto_synapse

from mining.proxy import core_miner
from mining.proxy.operations import abstract_operation
from models import base_models, synapses
from operation_logic import inpaint_logic

operation_name = "InpaintOperation"

T = TypeVar("T", bound=bt.Synapse)


class InpaintOperation(abstract_operation.Operation):
    @staticmethod
    async def forward(synapse: synapses.Inpaint) -> synapses.Inpaint:
        output = await inpaint_logic.inpaint_logic(base_models.InpaintIncoming(**synapse.model_dump()))

        synapse.init_image = None
        synapse.mask_image = None

        output_dict = output.model_dump()
        for field in output_dict:
            setattr(synapse, field, output_dict[field])

        return synapse

    @staticmethod
    async def blacklist(synapse: synapses.Inpaint) -> Tuple[bool, str]:
        return core_miner.base_blacklist(synapse)

    @staticmethod
    async def priority(synapse: synapses.Inpaint) -> float:
        return core_miner.base_priority(synapse)
