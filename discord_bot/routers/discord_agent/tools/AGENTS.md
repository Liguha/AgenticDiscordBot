# Agent Tools Rules

## Rules
- Docstrings are mandatory (used for LLM JSON schema autogeneration).
- `Args` section in docstrings MUST NOT include service fields (`broker`, `client`, `guild`, `state`).
- Always pass `broker: EventBroker` explicitly.
- State parameter: annotate with specific state model type (e.g. `AudioPlayerState`) or `None` if stateless, returning `tuple[ToolResult | ToolError, StateType]`.
- **Minimize token consumption**: tool schemas, docstrings, and result payloads are all billed as LLM context, so keep them lean. Only include fields the caller genuinely needs — drop redundant echoes (e.g. the query the agent already knows, a separate "answer"/"top_link" when the answer is derivable from `results`). Prefer `str`/`int` primitives and compact model shapes over deeply nested or duplicated data. If a field adds no new information for the agent, remove it rather than tolerating waste.

## Boilerplate
```python
from discord import Client, Guild
from .base import ToolResult, ToolError, Tool
from ....state_types import CustomState  # Use specific BaseState subclass or None
from ....events import EventBroker

__all__ = ["YourCustomResult", "your_custom_tool"]

class YourCustomResult(ToolResult):
    ...

@Tool
async def your_custom_tool(broker: EventBroker, 
                           client: Client, 
                           guild: Guild, 
                           state: CustomState, 
                           ...   # args with explicit Python 3.12 type annotations
                          ) -> tuple[YourCustomResult | ToolError, CustomState]:
    """Here docstrings for JSON schema autogen.

    Args:
        arg1: Single line description for argument.

    Returns:
        Optional. Describe only result without state.
    """
    ...
    return result, state
```
