# Rules
- One file - one pair of commands (`MessageCommand` and `InteractionCommand`).
- Module (file) description is a command description.
- `base.py` contains command base classes (`MessageCommand`, `InteractionCommand`, `CallbackPostprocessing`).
- Explicitly pass `broker: EventBroker` as a parameter to all commands.
- For state parameter: annotate with specific state type (e.g. `AudioPlayerState`, `PrefixState`) and return updated state. If command uses no state, annotate `state: None` and return/pass `None`.
- The decorators convert the function into a wrapper instance at import time (see `AGENTS.md`).

# Boilerplate
```python
"""COMMAND DESCRIPTION HERE"""

from discord import Interaction, Message, Client
from .base import InteractionCommand, MessageCommand
from ....events import EventBroker
from ....state_types import CustomState  # Or None if stateless

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

@InteractionCommand.add_descriptions(**ARGS_DESC)
@InteractionCommand.with_name("COMMAND_NAME")
async def interaction_COMMAND_NAME(broker: EventBroker, interaction: Interaction, state: CustomState, ...) -> CustomState:
    ...
    return state

# Optional: autocomplete for an option
@InteractionCommand.add_descriptions(**ARGS_DESC)
@InteractionCommand.add_autocompletes(command=command_autocomplete)  # callback returns list[InteractionCommand.Choice]
@InteractionCommand.with_name("COMMAND_NAME")
async def interaction_COMMAND_NAME(...): ...
```

# Option types
- `InteractionCommand.Range[int, 1, MAX]` → Discord `min_value`/`max_value` INTEGER constraints.
- `Literal["a", "b"]` on a parameter → fixed choice list in the slash payload.
- `InteractionCommand.Choice` → named/value pair for autocomplete suggestions.
- `InteractionCommand.add_autocompletes(command=cb)` → enables autocomplete on that option; callback is `async def cb(interaction, current) -> list[InteractionCommand.Choice]`.

# Registration & routing
- `InteractionCommand.register_all(client)` builds payloads from signatures and uploads via `client.http.bulk_upsert_global_commands` (no `CommandTree`).
- Slash routing keys on `interaction.type is InteractionType.application_command` + `interaction.data["name"]`; the router defers then calls `func.evaluate(...)`. Autocomplete interactions are dispatched via `InteractionCommand.dispatch_autocomplete`.

# Notes
- `discord.app_commands` does not exist (repo uses pycord 2.8.1, which replaces `app_commands` with `discord.commands`).
- This is not standard pycord `@slash_command`/`Bot` usage; the command system here is custom (`base.py`), built on raw gateway `interaction` events.