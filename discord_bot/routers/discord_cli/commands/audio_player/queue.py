"""Command to display the current track and upcoming audio playback queue."""

from discord import Interaction, Message, Client
from .config import GROUP_ID
from ..base import MessageCommand, InteractionCommand
from .....events import EventBroker
from .....state_types import AudioPlayerState

__all__ = ["message_queue", "interaction_queue"]

def format_queue(state: AudioPlayerState) -> str:
    if not state.current_track and not state.queue:
        return "🎵 The audio player queue is currently empty."
    lines = []
    if state.current_track:
        lines.append(f"▶️ **Now Playing:** {state.current_track.title}")
    else:
        lines.append("▶️ **Now Playing:** Nothing")
    if state.queue:
        lines.append("\n📋 **Upcoming Queue:**")
        for idx, track in enumerate(state.queue, start=1):
            lines.append(f"  **{idx}.** {track.title}")
    else:
        lines.append("\n📋 No upcoming tracks in the queue.")
    if state.is_looping:
        lines.append("\n🔄 Loop mode is currently enabled.")
    return "\n".join(lines)

@MessageCommand.with_name("queue", group_id=GROUP_ID)
async def message_queue(broker: EventBroker, client: Client, message: Message, state: AudioPlayerState | None) -> AudioPlayerState:
    if state is None:
        state = AudioPlayerState()
    content = format_queue(state)
    await message.reply(content)
    return state


@InteractionCommand.with_name("queue", group_id=GROUP_ID)
async def interaction_queue(broker: EventBroker, interaction: Interaction, state: AudioPlayerState | None) -> AudioPlayerState:
    if state is None:
        state = AudioPlayerState()
    content = format_queue(state)
    await interaction.followup.send(content)
    return state