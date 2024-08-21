from enum import Enum
from typing import Dict


class Task(Enum):
    # TODO: REMOVE ON NEXT DEPLOY AFTER 8TH OF AUGUST
    chat_mixtral = "chat-mixtral"
    chat_llama_3 = "chat-llama-3"
    playground_text_to_image = "playground-text-to-image"
    playground_image_to_image = "playground-image-to-image"
    ###

    chat_llama_3_1_8b = "chat-llama-3-1-8b"
    chat_llama_3_1_70b = "chat-llama-3-1-70b"

    proteus_text_to_image = "proteus-text-to-image"
    flux_schnell_text_to_image = "flux-schnell-text-to-image"
    dreamshaper_text_to_image = "dreamshaper-text-to-image"

    proteus_image_to_image = "proteus-image-to-image"
    flux_schnell_image_to_image = "flux-schnell-image-to-image"
    dreamshaper_image_to_image = "dreamshaper-image-to-image"

    # upscale = "upscale"

    jugger_inpainting = "inpaint"
    clip_image_embeddings = "clip-image-embeddings"
    avatar = "avatar"


TASK_TO_MAX_CAPACITY: Dict[Task, int] = {
    Task.chat_mixtral: 576_000,
    Task.chat_llama_3: 576_000,
    Task.playground_text_to_image: 10_000,
    Task.playground_image_to_image: 10_000,
    #
    Task.chat_llama_3_1_8b: 1_500_000,
    Task.chat_llama_3_1_70b: 576_000,
    #
    Task.proteus_text_to_image: 3_600,
    Task.flux_schnell_text_to_image: 3_600,
    Task.dreamshaper_text_to_image: 3_000,
    #
    Task.proteus_image_to_image: 3_600,
    Task.flux_schnell_image_to_image: 3_600,
    Task.dreamshaper_image_to_image: 3_000,
    #
    # Task.upscale: 100,
    #
    Task.jugger_inpainting: 4_000,
    Task.avatar: 1_120,
    Task.clip_image_embeddings: 0,  # disabled clip for now
}
