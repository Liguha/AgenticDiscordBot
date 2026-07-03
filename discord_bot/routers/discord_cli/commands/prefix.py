"""Configure the command prefix for text-based message commands."""

from discord import app_commands, Interaction, Message, Client
from .base import MessageCommand, InteractionCommand
from ....events import EventBroker
from ....state_types import PrefixState

__all__ = ["message_prefix", "interaction_prefix"]

ARGS_DESC = {
    "new_prefix": "The new character or string to use as the command prefix (e.g., !, ?, >>)"
}

@MessageCommand.add_descriptions(**ARGS_DESC)
@MessageCommand.with_name("prefix")
async def message_prefix(broker: EventBroker, client: Client, message: Message, state: PrefixState, new_prefix: str) -> PrefixState:
    new_state = state.model_copy(update={"prefix": new_prefix})
    await message.reply(f"New prefix is now: `{new_prefix}`")
    return new_state

@app_commands.describe(**ARGS_DESC)
@InteractionCommand.with_name("prefix")
async def interaction_prefix(broker: EventBroker, interaction: Interaction, state: PrefixState, new_prefix: str) -> PrefixState:
    new_state = state.model_copy(update={"prefix": new_prefix})
    await interaction.followup.send(f"New prefix is now: `{new_prefix}`")
    return new_state