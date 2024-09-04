import fastapi
from pydantic import BaseModel
import bittensor as bt
from core.bittensor_overrides import synapse as bto_synapse

bt.synapse = bto_synapse
from fastapi import HTTPException
from models import utility_models

#  All hacky backwards compatibility stuff
if not hasattr(BaseModel, "model_dump"):
    setattr(BaseModel, "model_dump", getattr(BaseModel, "dict"))
if not hasattr(BaseModel, "model_copy"):
    setattr(BaseModel, "model_copy", getattr(BaseModel, "copy"))
if not hasattr(BaseModel, "model_dump_json"):
    setattr(BaseModel, "model_dump_json", getattr(BaseModel, "json"))


class NSFWContentException(fastapi.HTTPException):
    def __init__(self, detail: str = "NSFW content detected"):
        super().__init__(status_code=fastapi.status.HTTP_403_FORBIDDEN, detail=detail)


def _do_nsfw_checks(formatted_response: BaseModel):
    if formatted_response is not None and formatted_response.is_nsfw:
        raise NSFWContentException()


def do_formatted_response_image_checks(formatted_response: BaseModel, result: utility_models.QueryResult):
    _do_nsfw_checks(formatted_response)
    if formatted_response is None or formatted_response.image_b64 is None:
        # return a 500 internal server error and intenrally log it
        bt.logging.error(f"Received a None result for some reason; Result error message: {result.error_message}")
        raise HTTPException(status_code=500, detail=result.error_message)
