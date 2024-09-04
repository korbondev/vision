import enum
from typing import Dict, List, Optional, Any

import numpy as np
from pydantic import ConfigDict, BaseModel
import bittensor as bt
from core.bittensor_overrides import synapse as bto_synapse

bt.synapse = bto_synapse

from core import Task
from validation.models import axon_uid

#  All hacky backwards compatibility stuff
if not hasattr(BaseModel, "model_dump"):
    setattr(BaseModel, "model_dump", getattr(BaseModel, "dict"))
if not hasattr(BaseModel, "model_copy"):
    setattr(BaseModel, "model_copy", getattr(BaseModel, "copy"))
if not hasattr(BaseModel, "model_dump_json"):
    setattr(BaseModel, "model_dump_json", getattr(BaseModel, "json"))


class QueryResult(BaseModel):
    formatted_response: Any = None
    axon_uid: Optional[int] = None
    miner_hotkey: Optional[str] = None
    response_time: Optional[float] = None
    error_message: Optional[str] = None
    failed_axon_uids: List[int] = []
    task: Task
    status_code: Optional[int] = None
    success: bool


class ChatModels(str, enum.Enum):
    """Model is used for the chat"""

    llama_3_1_8b = "llama-3-1-8b"
    mixtral = "mixtral-8x7b"
    llama_3 = "llama-3"
    llama_3_1_70b = "llama-3-1-70b"


class Role(str, enum.Enum):
    """Message is sent by which role?"""

    user = "user"
    assistant = "assistant"
    system = "system"


class Message(BaseModel):
    role: Role = Role.user
    content: str = "Remind me that I have forgot to set the messages"
    model_config = ConfigDict(extra="allow")


class UIDinfo(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    uid: axon_uid
    hotkey: str
    axon: bt.chain_data.AxonInfo


class OperationDistribution(BaseModel):
    available_axons: List[int]
    probabilities: List[float]
    score_discounts: Dict[int, float]

    def get_order_of_axons_to_query(self) -> List[int]:
        z = -np.log(-np.log(np.random.uniform(0, 1, len(self.available_axons))))
        scores = np.log(self.probabilities) + z
        return [self.available_axons[i] for i in np.argsort(-scores)]


class EngineEnum(str, enum.Enum):
    DREAMSHAPER = "dreamshaper"
    PLAYGROUND = "playground"
    PROTEUS = "proteus"
    FLUX = "flux-schnell"


class ImageHashes(BaseModel):
    average_hash: str = ""
    perceptual_hash: str = ""
    difference_hash: str = ""
    color_hash: str = ""


class ImageResponseBody(BaseModel):
    image_b64: Optional[str] = None
    is_nsfw: Optional[bool] = None
    clip_embeddings: Optional[List[float]] = None
    image_hashes: Optional[ImageHashes] = None


class MinerChatResponse(BaseModel):
    text: str
    logprob: float
