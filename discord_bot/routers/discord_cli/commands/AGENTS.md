# CLI Commands Rules

## Rules
- One file - one pair of commands (`MessageCommand` and `InteractionCommand`).
- Module (file) docstring is the command description.
- `base.py` contains command base classes (`MessageCommand`, `InteractionCommand`, `CallbackPostprocessing`).
- Always pass `broker: EventBroker` explicitly.
- For state parameter: annotate with specific state model type (e.g., `AudioPlayerState`, `PrefixState`) and return the updated state. If command uses no state, annotate `state: None` and return/pass `None`.

## Boilerplate
```python
"""COMMAND DESCRIPTION HERE"""

from discord import app_commands, Interaction, Message, Client
from .base import MessageCommand, InteractionCommand
from ....events import EventBroker
from ....state_types import CustomState  # Use specific BaseState subclass or None

__all__ = ["message_COMMAND_NAME", "interaction_COMMAND_NAME"]

ARGS_DESC = {
    "ARG_1": "ARG_1 DESCRIPTION",
    "ARG_n": "ARG_n DESCRIPTION"
}

@MessageCommand.add_descriptions(**ARGS_DESC)
@MessageCommand.with_name("COMMAND_NAME")
async def message_COMMAND_NAME(broker: EventBroker, client: Client, message: Message, state: CustomState, ...) -> CustomState:
    ...
    return state

@app_commands.describe(**ARGS_DESC)
@InteractionCommand.with_name("COMMAND_NAME")
async def interaction_COMMAND_NAME(broker: EventBroker, interaction: Interaction, state: CustomState, ...) -> CustomState:
    ...
    return state
```
