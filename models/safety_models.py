from pydantic import BaseModel

if not hasattr(BaseModel, "model_dump"):
    setattr(BaseModel, "model_dump", getattr(BaseModel, "dict"))


class CheckImageRequest(BaseModel):
    image_b64: str
