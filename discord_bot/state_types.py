from pydantic import BaseModel

__all__ = ["PrefixState"]

class PrefixState(BaseModel):
    prefix: str
