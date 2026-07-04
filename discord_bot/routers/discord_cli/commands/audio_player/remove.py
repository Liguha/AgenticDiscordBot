"""Command to remove a track or a range of tracks from the playback queue using 1-based indexing."""

from discord import app_commands, Interaction, Message, Client
from .config import GROUP_ID
from ..base import MessageCommand, InteractionCommand
from .....actions import remove_range
from .....events import EventBroker
from .....state_types import AudioPlayerState

__all__ = ["message_remove", "interaction_remove"]

ARGS_DESC = {
    "start_pos": "The 1-based position of the first track to remove (matching the queue list).",
    "end_pos": "The 1-based position of the exclusive end track. Optional."
}

@MessageCommand.add_descriptions(**ARGS_DESC)
@MessageCommand.with_name("remove", group_id=GROUP_ID)
async def message_remove(broker: EventBroker, client: Client, message: Message, state: AudioPlayerState, start_pos: int, end_pos: int | None = None) -> AudioPlayerState:
    start_idx = start_pos - 1
    actual_end = start_pos if end_pos is None else end_pos
    removed_count, new_state = await remove_range(broker, client, state, start_idx, actual_end)
    if removed_count > 0:
        await message.reply(f"🗑️ Successfully removed {removed_count} track(s) from the queue.")
    else:
        await message.reply("❌ Invalid track positions specified or queue is empty.")
    return new_state

@app_commands.describe(**ARGS_DESC)
@InteractionCommand.with_name("remove", group_id=GROUP_ID)
async def interaction_remove(broker: EventBroker, interaction: Interaction, state: AudioPlayerState, start_pos: int, end_pos: int | None = None) -> AudioPlayerState:
    start_idx = start_pos - 1
    actual_end = start_pos if end_pos is None else end_pos
    removed_count, new_state = await remove_range(broker, interaction.client, state, start_idx, actual_end)
    if removed_count > 0:
        await interaction.followup.send(f"🗑️ Successfully removed {removed_count} track(s) from the queue.")
    else:
        await interaction.followup.send("❌ Invalid track positions specified or queue is empty.")
    return new_state