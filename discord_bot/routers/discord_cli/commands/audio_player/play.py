"""Command to search and play audio tracks with interactive selection when a limit is provided."""

import asyncio
import discord
import shlex
from typing import Any, Callable, get_args
from functools import lru_cache
from argparse import ArgumentParser
from .config import GROUP_ID
from discord import app_commands, Interaction, Message, Client
from ..base import MessageCommand, InteractionCommand, CallbackPostprocessing
from .....actions import join_voice_to_user, search_audio, add_track, on_track_finished, TRACK_FINISHED_CALLBACK_NAME
from .....events import EventBroker
from .....state_types import AudioPlayerState, AudioSourceType

__all__ = ["message_play", "interaction_play", "callback_track_finished"]


PLATFORMS = get_args(AudioSourceType)
ARGS_DESC = {
    "query": "The title, search keywords, or URL of the track you want to play.",
    "platform": f"The streaming platform to search on ({'/'.join(PLATFORMS)}).",
    "limit": "The maximum number of search results to retrieve and choose from."
}

class TrackSelectView(discord.ui.View):
    def __init__(self, tracks: list[Any], author_id: int):
        super().__init__(timeout=30.0)
        self.tracks = tracks
        self.author_id = author_id
        self.selected_track = None
        options = []
        for i, track in enumerate(tracks):
            label = f"{i+1}. {track.title}"[:100]
            options.append(discord.SelectOption(label=label, value=str(i)))
        self.select = discord.ui.Select(
            placeholder="Choose a track to play...",
            min_values=1,
            max_values=1,
            options=options
        )
        self.select.callback = self.select_callback
        self.add_item(self.select)

    async def select_callback(self, interaction: Interaction):
        if interaction.user.id != self.author_id:
            await interaction.response.send_message("❌ This selection menu is not for you.", ephemeral=True)
            return
        idx = int(self.select.values[0])
        self.selected_track = self.tracks[idx]
        self.stop()
        await interaction.response.defer()

    async def on_timeout(self):
        self.stop()


@lru_cache(maxsize=1)
def parse_play_flags(message_content: str) -> dict[str, Any]:
    parts = message_content.split(maxsplit=1)
    tokens = shlex.split(parts[1]) if len(parts) > 1 else []
    parser = ArgumentParser()
    parser.add_argument("query", nargs="*")
    parser.add_argument("--platform", "-p", default="youtube")
    parser.add_argument("--limit", "-l", type=int, default=1)
    args, _ = parser.parse_known_args(tokens)
    return {
        "query": " ".join(args.query),
        "platform": args.platform,
        "limit": args.limit
    }

@MessageCommand.add_parsers(
    query=lambda token, client, msg: parse_play_flags(msg.content)["query"],
    platform=lambda token, client, msg: parse_play_flags(msg.content)["platform"],
    limit=lambda token, client, msg: parse_play_flags(msg.content)["limit"]
)
@MessageCommand.add_descriptions(**ARGS_DESC)
@MessageCommand.with_name("play", group_id=GROUP_ID)
async def message_play(broker: EventBroker,
                       client: Client,
                       message: Message,
                       state: AudioPlayerState,
                       query: str,
                       platform: AudioSourceType = "youtube",
                       limit: int = 1
                      ) -> AudioPlayerState:
    guild = message.guild
    joined, _ = await join_voice_to_user(broker, client, None, guild, message.author)
    if not joined and not guild.voice_client:
        await message.reply("❌ You must be in a voice channel for me to join and play music!")
        return state
    tracks, _ = await search_audio(broker, client, None, query, source_type=platform, limit=limit)
    if not tracks:
        await message.reply("❌ No matching results found for your search query.")
        return state
    if limit > 1 and len(tracks) > 1:
        msg_content = (
            "🔍 **Search Results:**\n" + 
            "\n".join(f"**{i+1}.** {t.title}" for i, t in enumerate(tracks)) + 
            "\n\n🔢 Reply with the track number you want to play (or type `cancel`)."
        )
        await message.reply(msg_content)
        check: Callable[[Message], bool] = lambda m: m.author.id == message.author.id and m.channel.id == message.channel.id
        try:
            response = await client.wait_for("message", check=check, timeout=30.0)
            content = response.content.strip()
            if content.lower() == "cancel":
                await message.reply("❌ Selection cancelled.")
                return state
            idx = int(content) - 1
            if 0 <= idx < len(tracks):
                chosen_track = tracks[idx]
            else:
                await message.reply("❌ Invalid track selection number. Out of range.")
                return state
        except (ValueError, IndexError):
            await message.reply("❌ Invalid text input received. Selection aborted.")
            return state
        except asyncio.TimeoutError:
            await message.reply("❌ Selection timed out.")
            return state
    else:
        chosen_track = tracks[0]
    _, new_state = await add_track(broker, client, state, guild, chosen_track)
    await message.reply(f"➕ Added to queue: **{chosen_track.title}**")
    return new_state


@app_commands.describe(**ARGS_DESC)
@InteractionCommand.with_name("play", group_id=GROUP_ID)
async def interaction_play(broker: EventBroker,
                           interaction: Interaction,
                           state: AudioPlayerState,
                           query: str,
                           platform: AudioSourceType = "youtube",
                           limit: int = 1
                          ) -> AudioPlayerState:
    guild = interaction.guild
    joined, _ = await join_voice_to_user(broker, interaction.client, None, guild, interaction.user)
    if not joined and not guild.voice_client:
        await interaction.followup.send("❌ You must be in a voice channel for me to join and play music!")
        return state
    tracks, _ = await search_audio(broker, interaction.client, None, query, source_type=platform, limit=limit)
    if not tracks:
        await interaction.followup.send("❌ No matching results found for your search query.")
        return state
    if limit > 1 and len(tracks) > 1:
        view = TrackSelectView(tracks, interaction.user.id)
        msg: Message = await interaction.followup.send("🔍 Multiple results found. Please choose one from the dropdown:", view=view)
        await view.wait()
        if view.selected_track is None:
            await interaction.followup.send("❌ Selection timed out or was cancelled.")
            return state
        chosen_track = view.selected_track
        try:
            await interaction.followup.edit_message(msg.id, content=f"✅ Choice Confirmed: **{chosen_track.title}**", view=None)
        except Exception:
            pass
    else:
        chosen_track = tracks[0]
    _, new_state = await add_track(broker, interaction.client, state, guild, chosen_track)
    await interaction.followup.send(f"➕ Added to queue: **{chosen_track.title}**")
    return new_state

@CallbackPostprocessing.with_name(TRACK_FINISHED_CALLBACK_NAME, group_id=GROUP_ID)
async def callback_track_finished(state: AudioPlayerState, payload: dict[str, Any]) -> AudioPlayerState:
    return await on_track_finished(state, payload)