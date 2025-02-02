import pybase64 as base64
from typing import Dict
import numpy as np
from PIL import Image
import cv2
import random
from io import BytesIO
import io
import binascii
from mining.db.db_management import miner_db_manager


# Would people want this to be in a DB instead which is read on every request, but then more configurable?
def load_concurrency_groups(hotkey: str) -> Dict[str, float]:
    return miner_db_manager.load_concurrency_groups()


def load_capacities(hotkey: str) -> Dict[str, Dict[str, float]]:
    return miner_db_manager.load_task_capacities(hotkey)


def generate_mask_with_circle(image_b64: str) -> np.ndarray:
    imgdata = base64.b64decode(image_b64)
    image = Image.open(BytesIO(imgdata))
    image_np = np.array(image)

    image_shape = image_np.shape[:2]

    center_x = np.random.randint(0, image_shape[1])
    center_y = np.random.randint(0, image_shape[0])
    center = (center_x, center_y)

    mask = np.zeros(image_shape, np.uint8)

    radius = random.randint(20, 100)

    cv2.circle(mask, center, radius, (1), 1)

    mask = cv2.floodFill(mask, None, center, 1)[1]
    mask_img = Image.fromarray(mask, "L")
    buffered = BytesIO()
    mask_img.save(buffered, format="PNG")
    mask_img_str = base64.b64encode(buffered.getvalue()).decode("utf-8")
    return mask_img_str


def pil_to_base64(image: Image, format: str = "JPEG") -> str:
    buffered = io.BytesIO()
    image.save(buffered, format=format)
    img_str = base64.b64encode(buffered.getvalue()).decode()
    return img_str


def base64_to_pil(image_b64: str) -> Image.Image:
    try:
        image_data = base64.b64decode(image_b64)
        image = Image.open(io.BytesIO(image_data))
        return image
    except binascii.Error:
        return None


def get_seed(seed_chunk_size: int, validator_uid: int) -> int:
    return random.randint(
        seed_chunk_size * validator_uid,
        seed_chunk_size * (validator_uid + 1) - 1,
    )
