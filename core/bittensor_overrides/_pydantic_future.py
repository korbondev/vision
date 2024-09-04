from pydantic import BaseModel
# hacky workaround for pydantic < 2.0


def future_dump(pydantic_object: BaseModel):
    """Backwards compatible pydantic dumping function
    This is to maintain compatability with both pydantic < 2.0 and >= 2.0 versions
    For > 2.0, the method is called `model_dump()`, and for < 2.0 it is `dict()`

    Args:
    - pydantic_object: The object to be dumped

    Returns:
    - The dumped object
    """
    try:
        return pydantic_object.model_dump()
    except AttributeError:
        return pydantic_object.dict()
