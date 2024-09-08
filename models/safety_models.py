
from pydantic import BaseModel


from functools import lru_cache
class SCBaseModel(BaseModel):
    @classmethod
    @lru_cache()
    def get_schema(cls):
        return cls.schema()
    
class CheckImageRequest(SCBaseModelBaseModel):
    image_b64: str
