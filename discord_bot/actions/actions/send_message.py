from typing import Any
from functools import partial
from discord import Guild, TextChannel
from ..structs import ExecutionContext, ActionResult, DiscordData
from ..wrapper import Action
from ...enums import PlatformEnum

__all__ = ["send_message"]

@Action
async def send_message(ctx: ExecutionContext[Any], state: None, msg: str) -> tuple[ActionResult[None], None]:
    deffered_calls = []
    match ctx.platform:
        case PlatformEnum.DISCORD:
            ctx_data: DiscordData = ctx.data
            text_ch = ctx_data.text_channel or ctx_data.guild.text_channels[0]
            deffered_calls.append(partial(text_ch.send, msg))
        case _:
            raise ValueError(f"Can't send messge to platform `{ctx.platform}`")
    return (ActionResult(None, deffered_calls), None)
    