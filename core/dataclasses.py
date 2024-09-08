from typing import Optional

from bittensor.chain_data import AxonInfo
from pydantic import BaseModel

from functools import lru_cache
class SCBaseModel(BaseModel):
    @classmethod
    @lru_cache()
    def get_schema(cls):
        return cls.schema()
    
class Model(SCBaseModel):
    class Config:
        arbitrary_types_allowed = True


class Axon(Model):
    index: int
    uid: str
    hotkey: str
    coldkey: str
    incentive: float
    bt_axon: AxonInfo


class TextPrompt(SCBaseModel):
    text: str
    weight: Optional[float]
