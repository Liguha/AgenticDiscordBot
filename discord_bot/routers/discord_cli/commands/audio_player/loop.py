"""Command to toggle looping configuration for the current playback session."""

from discord import Interaction, Message, Client
from .config import GROUP_ID
from ..base import MessageCommand, InteractionCommand
from .....actions import toggle_loop
from .....events import EventBroker
from .....state_types import AudioPlayerState

__all__ = ["message_loop", "interaction_loop"]

@MessageCommand.with_name("loop", group_id=GROUP_ID)
async def message_loop(broker: EventBroker, client: Client, message: Message, state: AudioPlayerState) -> AudioPlayerState:
    is_looping, new_state = await toggle_loop(broker, client, state)
    status = "enabled" if is_looping else "disabled"
    await message.reply(f"🔄 Loop mode has been **{status}**.")
    return new_state

@InteractionCommand.with_name("loop", group_id=GROUP_ID)
async def interaction_loop(broker: EventBroker, interaction: Interaction, state: AudioPlayerState) -> AudioPlayerState:
    is_looping, new_state = await toggle_loop(broker, interaction.client, state)
    status = "enabled" if is_looping else "disabled"
    await interaction.followup.send(f"🔄 Loop mode has been **{status}**.")
    return new_state