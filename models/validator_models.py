from pydantic import BaseModel
from core import Task

if not hasattr(BaseModel, "model_dump"):
    setattr(BaseModel, "model_dump", getattr(BaseModel, "dict"))
if not hasattr(BaseModel, "model_copy"):
    setattr(BaseModel, "model_copy", getattr(BaseModel, "copy"))


class TaskStatsForUID(BaseModel):
    uid: int
    task: Task
    current_volume: float
    quality_score: float
    volume_reliability_score: float
