from discord import Client, TextChannel
from ..wrapper import Action

__all__ = ["send_message"]

@Action
async def send_message(client: Client, state: None, channel: TextChannel, msg: str) -> tuple[None, None]:
    await channel.send(msg)
    return None, None
    