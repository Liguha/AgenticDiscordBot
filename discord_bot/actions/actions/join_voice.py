from discord import Client, Guild, VoiceChannel, User, VoiceClient, Member, HTTPException
from ..wrapper import Action
from ...events import EventBroker

__all__ = ["join_voice", "join_voice_to_user"]

@Action
async def join_voice(broker: EventBroker, client: Client, state: None, guild: Guild, channel: VoiceChannel) -> tuple[bool, None]:
    vc: VoiceClient | None = guild.voice_client
    if vc is not None:
        if vc.channel.id != channel.id:
            await vc.move_to(channel)
            return True, None
        return False, None
    await channel.connect()
    return True, None

@Action
async def join_voice_to_user(broker: EventBroker, client: Client, state: None, guild: Guild, user: User) -> tuple[bool, None]:
    member: Member | None = guild.get_member(user.id)
    if member is None:
        return False, None
    if member.voice is None or member.voice.channel is None:
        return False, None
    target_channel = member.voice.channel
    if target_channel is None:
        return False, None
    return await join_voice(broker, client, state, guild, target_channel)