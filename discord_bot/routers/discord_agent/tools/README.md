# Rules
- Docstrings are mandatory
- `Args` section shouldn't include service fields `broker`, `client`, `guild`, `state`

# Boilerplate
```py
from discord import Client, Guild
from .base import ToolResult, ToolError, Tool
from ....state_types import BaseState
from ....events import EventBroker

__all__ = ["YourCustomResult", "your_custom_tool"]

class YourCustomResult(ToolResult):
    ...

@Tool
async def your_custom_tool(broker: EventBroker, 
                           client: Client, 
                           guild: Guild, 
                           state: BaseState, 
                           ...   # args with type annotations
                          ) -> tuple[YourCustomResult | ToolError, BaseState]:
    """Here docstrings for JSON scheme autogen.

    Args:
        arg1: Single line description for argument.
        ...

    Returns:
        Optional. Describe only result without state.
    """
    ...
```