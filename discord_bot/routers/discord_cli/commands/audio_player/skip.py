"""Command to skip the currently playing audio track."""

from discord import Interaction, Message, Client
from .config import GROUP_ID
from ..base import MessageCommand, InteractionCommand
from .....actions import skip_track
from .....events import EventBroker
from .....state_types import AudioPlayerState

__all__ = ["message_skip", "interaction_skip"]

@MessageCommand.with_name("skip", group_id=GROUP_ID)
async def message_skip(broker: EventBroker, client: Client, message: Message, state: AudioPlayerState) -> AudioPlayerState:
    success, new_state = await skip_track(broker, client, state, message.guild)
    if success:
        await message.reply("⏭️ Skipped the current track.")
    else:
        await message.reply("❌ Nothing is currently playing.")
    return new_state

@InteractionCommand.with_name("skip", group_id=GROUP_ID)
async def interaction_skip(broker: EventBroker, interaction: Interaction, state: AudioPlayerState) -> AudioPlayerState:
    success, new_state = await skip_track(broker, interaction.client, state, interaction.guild)
    if success:
        await interaction.followup.send("⏭️ Skipped the current track.")
    else:
        await interaction.followup.send("❌ Nothing is currently playing.")
    return new_state