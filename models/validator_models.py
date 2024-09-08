from pydantic import BaseModel
from core import Task

from functools import lru_cache
class SCBaseModel(BaseModel):
    @classmethod
    @lru_cache()
    def get_schema(cls):
        return cls.schema()
    
class TaskStatsForUID(SCBaseModel):
    uid: int
    task: Task
    current_volume: float
    quality_score: float
    volume_reliability_score: float

