# CLI Commands Rules

## Dialect: Wrapper instances, not functions
The command module uses the project's "decorator class" dialect. The decorators turn the raw function into a **`MessageCommand` / `InteractionCommand` instance at import time**; the module-level `message_X`/`interaction_X` names are instances, not functions. Registry (`COMMANDS`, `_INTERACTIONS_LIST`) population happens inside the class `__init__`. See root `AGENTS.md` → "The Decorator Class Dialect".

## Rules
- One file - one pair of commands (`MessageCommand` and `InteractionCommand`).
- Module (file) docstring is the command description.
- `base.py` contains command base classes (`MessageCommand`, `InteractionCommand`, `CallbackPostprocessing`).
- Always pass `broker: EventBroker` explicitly.
- For state parameter: annotate with specific state model type (e.g., `AudioPlayerState`, `PrefixState`) and return the updated state. If command uses no state, annotate `state: None` and return/pass `None`.

## Decorator chain (order matters)
The `add_*` decorator MUST sit directly above `with_name`, and the `with_name` decorator MUST be the innermost (immediately over `async def`). Bottom-to-top evaluation instantiates the command first, then the `add_*` decorators mutate the resulting instance. The chain forms a single expression; the object registers itself on creation. Do not reorder or split it.

`MessageCommand`:
```python
@MessageCommand.add_descriptions(**ARGS_DESC)
@MessageCommand.add_parsers(**PARSERS)        # optional: text→value parsers for message commands
@MessageCommand.with_name("COMMAND_NAME")
async def message_COMMAND_NAME(broker: EventBroker, client: Client, message: Message, state: CustomState, ...) -> CustomState:
    ...
    return state
```

`InteractionCommand`:
```python
@InteractionCommand.add_descriptions(**ARGS_DESC)
@InteractionCommand.add_autocompletes(command=command_autocomplete)   # optional
@InteractionCommand.with_name("COMMAND_NAME")
async def interaction_COMMAND_NAME(broker: EventBroker, interaction: Interaction, state: CustomState, ...) -> CustomState:
    ...
    return state
```

## Parameter order & injection
The first three positional parameters are always injected by the framework and never come from user input:
- `MessageCommand`: `broker, client, message, state, ...` (user args after `state`)
- `InteractionCommand`: `broker, interaction, state, ...` (user args after `state`)

Remaining parameters are the command's user-facing options, typed with standard annotations or `InteractionCommand.Range` / `InteractionCommand.Literal` (see below).

## Interaction options, descriptions, autocomplete
- **Descriptions**: `@InteractionCommand.add_descriptions(**ARGS_DESC)` populates per-option descriptions automatically (mirrors `MessageCommand.add_descriptions`).
- **Autocomplete**: declare via `@InteractionCommand.add_autocompletes(command=command_autocomplete)`; the callback signature is `async def command_autocomplete(interaction: Interaction, current: str) -> list[InteractionCommand.Choice]`. Autocomplete interactions are delivered through the same `interaction` gateway event; the CLI router calls `InteractionCommand.dispatch_autocomplete(interaction)` for `auto_complete`-type interactions.
- **Ranges**: `limit: InteractionCommand.Range[int, 1, MAX] = 3` produces Discord `min_value`/`max_value` INTEGER constraints in the registered option payload.
- **Choices** (from `Literal`): a parameter annotated `platform: Literal["youtube", "soundcloud"]` is emitted as a fixed choice list (select menu) in the slash payload.
- `Range` / `Choice` are **nested classes of `InteractionCommand`** (`InteractionCommand.Range[int, ...]`, `InteractionCommand.Choice(...)`) — not top-level symbols, and `discord.app_commands` does NOT exist (this repo uses pycord 2.8.1, which provides no `app_commands` module).

## Registration & routing
- `InteractionCommand.register_all(client)` builds the payloads from function signatures (`command_payload()`) and uploads via `client.http.bulk_upsert_global_commands(application_id, payload)` — no pycord `Bot` / `CommandTree` involved. It is called once at startup before `client.connect()`.
- Slash commands are routed by `interaction.type is InteractionType.application_command` and `interaction.data["name"]`; the router calls `interaction.response.defer()` then `func.evaluate(broker, interaction, state, **options)`.

## Boilerplate
```python
"""COMMAND DESCRIPTION HERE"""

from discord import Interaction, Message, Client
from .base import InteractionCommand, MessageCommand
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

@InteractionCommand.add_descriptions(**ARGS_DESC)
@InteractionCommand.with_name("COMMAND_NAME")
async def interaction_COMMAND_NAME(broker: EventBroker, interaction: Interaction, state: CustomState, ...) -> CustomState:
    ...
    return state
```

For autocomplete options use `@InteractionCommand.add_autocompletes(command=command_autocomplete)` with a callback returning `list[InteractionCommand.Choice]`.