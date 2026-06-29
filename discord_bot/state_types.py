from pydantic import BaseModel

__all__ = ["Model"]

# TODO: remove it, just for testing
class Model(BaseModel):
    x: int
    y: float
