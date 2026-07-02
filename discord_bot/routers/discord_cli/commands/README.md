# Rules
- One file - one pair of commands
- Module (file) description is a command description
- `base.py` is very specific one.

# Boilerplate
```py
"""COMMAND DESCRIPTION HERE"""

from discord import app_commands, Interaction, Message, Client
from .base import MessageCommand, InteractionCommand

__all__ = ["message_COMMAND_NAME", "interaction_COMMAND_NAME"]

ARGS_DESC = {
    "ARG_1": "ARG_1 DESCRIPTION",
    ...
    "ARG_n": "ARG_n DESCRIPTION"
}

@MessageCommand.add_descriptions(**ARGS_DESC)
@MessageCommand.with_name("COMMAND_NAME")
async def message_COMMAND_NAME(client: Client, message: Message, state: ..., ...) -> None:
    ...

@app_commands.describe(**ARGS_DESC)
@InteractionCommand.with_name("COMMAND_NAME")
async def interaction_COMMAND_NAME(interaction: Interaction, state: ..., ...) -> None:
    ...
```