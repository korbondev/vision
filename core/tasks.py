"""Would prefer to make this just one dataclass"""

from enum import Enum
from pydantic import BaseModel
from core import Task
from models import synapses, utility_models
from typing import Dict, Optional
import bittensor as bt
from core.bittensor_overrides import synapse as bto_synapse

bt.synapse = bto_synapse
#  All hacky backwards compatibility stuff
if not hasattr(BaseModel, "model_dump"):
    setattr(BaseModel, "model_dump", getattr(BaseModel, "dict"))
if not hasattr(BaseModel, "model_copy"):
    setattr(BaseModel, "model_copy", getattr(BaseModel, "copy"))
if not hasattr(BaseModel, "model_dump_json"):
    setattr(BaseModel, "model_dump_json", getattr(BaseModel, "json"))

# I don't love this being here. How else should I do it though?
# I don't want to rely on any extra third party service for fetching this info...


TASK_IS_STREAM: Dict[Task, bool] = {
    Task.chat_mixtral: True,
    Task.chat_llama_3: True,
    Task.chat_llama_3_1_8b: True,
    Task.chat_llama_3_1_70b: True,
    #
    Task.playground_text_to_image: False,
    Task.playground_image_to_image: False,
    #
    Task.proteus_text_to_image: False,
    Task.flux_schnell_text_to_image: False,
    Task.dreamshaper_text_to_image: False,
    #
    Task.proteus_image_to_image: False,
    Task.flux_schnell_image_to_image: False,
    Task.dreamshaper_image_to_image: False,
    #
    # Task.upscale: False,
    #
    Task.jugger_inpainting: False,
    Task.avatar: False,
}
TASKS_TO_SYNAPSE: Dict[Task, bt.Synapse] = {
    Task.chat_mixtral: synapses.Chat,
    Task.chat_llama_3: synapses.Chat,
    Task.playground_text_to_image: synapses.TextToImage,
    Task.playground_image_to_image: synapses.ImageToImage,
    #
    Task.chat_llama_3_1_8b: synapses.Chat,
    Task.chat_llama_3_1_70b: synapses.Chat,
    #
    Task.proteus_text_to_image: synapses.TextToImage,
    Task.flux_schnell_text_to_image: synapses.TextToImage,
    Task.dreamshaper_text_to_image: synapses.TextToImage,
    #
    Task.proteus_image_to_image: synapses.ImageToImage,
    Task.flux_schnell_image_to_image: synapses.ImageToImage,
    Task.dreamshaper_image_to_image: synapses.ImageToImage,
    #
    # Task.upscale: synapses.Upscale,
    #
    Task.jugger_inpainting: synapses.Inpaint,
    Task.avatar: synapses.Avatar,
}


def get_task_from_synapse(synapse: bt.Synapse) -> Optional[Task]:
    if isinstance(synapse, synapses.Chat):
        if synapse.model == utility_models.ChatModels.mixtral.value:
            return Task.chat_mixtral
        elif synapse.model == utility_models.ChatModels.llama_3.value:
            return Task.chat_llama_3
        elif synapse.model == utility_models.ChatModels.llama_3_1_8b.value:
            return Task.chat_llama_3_1_8b
        elif synapse.model == utility_models.ChatModels.llama_3_1_70b.value:
            return Task.chat_llama_3_1_70b
        else:
            return None
    elif isinstance(synapse, synapses.TextToImage):
        if synapse.engine == utility_models.EngineEnum.PROTEUS.value:
            return Task.proteus_text_to_image
        elif synapse.engine == utility_models.EngineEnum.PLAYGROUND.value:
            return Task.playground_text_to_image
        elif synapse.engine == utility_models.EngineEnum.DREAMSHAPER.value:
            return Task.dreamshaper_text_to_image
        elif synapse.engine == utility_models.EngineEnum.FLUX.value:
            return Task.flux_schnell_text_to_image
        else:
            return None
    elif isinstance(synapse, synapses.ImageToImage):
        if synapse.engine == utility_models.EngineEnum.PROTEUS.value:
            return Task.proteus_image_to_image
        elif synapse.engine == utility_models.EngineEnum.PLAYGROUND.value:
            return Task.playground_image_to_image
        elif synapse.engine == utility_models.EngineEnum.DREAMSHAPER.value:
            return Task.dreamshaper_image_to_image
        elif synapse.engine == utility_models.EngineEnum.FLUX.value:
            return Task.flux_schnell_image_to_image
        else:
            return None
    elif isinstance(synapse, synapses.Inpaint):
        return Task.jugger_inpainting

    elif isinstance(synapse, synapses.Avatar):
        return Task.avatar

    # elif isinstance(synapse, synapses.Upscale):
    #     return Task.upscale
    else:
        return None


class TaskType(Enum):
    IMAGE = "image"
    TEXT = "text"
    # UPSCALE = "upscale"


class TaskConfig(BaseModel):
    task: Task
    overhead: float
    mean: float
    variance: float
    task_type: TaskType


TASK_CONFIGS = [
    # TaskConfig(task=Task.upscale, overhead=0.5, mean=0.80, variance=1, task_type=TaskType.UPSCALE),
    TaskConfig(task=Task.chat_llama_3_1_70b, overhead=0.3, mean=0.018, variance=130, task_type=TaskType.TEXT),
    TaskConfig(task=Task.chat_llama_3_1_8b, overhead=0.2, mean=0.009, variance=200, task_type=TaskType.TEXT),
    TaskConfig(task=Task.proteus_image_to_image, overhead=0.6, mean=0.24, variance=5, task_type=TaskType.IMAGE),
    TaskConfig(task=Task.proteus_text_to_image, overhead=0.25, mean=0.2, variance=7, task_type=TaskType.IMAGE),
    TaskConfig(task=Task.flux_schnell_text_to_image, overhead=0.4, mean=0.30, variance=7, task_type=TaskType.IMAGE),
    TaskConfig(task=Task.flux_schnell_image_to_image, overhead=0.6, mean=0.36, variance=5, task_type=TaskType.IMAGE),
    TaskConfig(task=Task.avatar, overhead=0.5, mean=0.50, variance=4, task_type=TaskType.IMAGE),
    TaskConfig(task=Task.dreamshaper_text_to_image, overhead=0.3, mean=0.22, variance=7, task_type=TaskType.IMAGE),
    TaskConfig(task=Task.dreamshaper_image_to_image, overhead=0.6, mean=0.28, variance=5, task_type=TaskType.IMAGE),
    TaskConfig(task=Task.jugger_inpainting, overhead=0.4, mean=0.3, variance=4, task_type=TaskType.IMAGE),
]


def get_task_config(task: Task) -> TaskConfig:
    for config in TASK_CONFIGS:
        if config.task == task:
            return config
    raise ValueError(f"Task configuration for {task.value} not found")
