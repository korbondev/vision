from typing import Optional

from bittensor.chain_data import AxonInfo
from pydantic import ConfigDict, BaseModel

if not hasattr(BaseModel, "model_dump"):
    setattr(BaseModel, "model_dump", getattr(BaseModel, "dict"))
if not hasattr(BaseModel, "model_copy"):
    setattr(BaseModel, "model_copy", getattr(BaseModel, "copy"))
if not hasattr(BaseModel, "model_dump_json"):
    setattr(BaseModel, "model_dump_json", getattr(BaseModel, "json"))


class Model(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)


class Axon(Model):
    index: int
    uid: str
    hotkey: str
    coldkey: str
    incentive: float
    bt_axon: AxonInfo


class TextPrompt(BaseModel):
    text: str
    weight: Optional[float] = None
