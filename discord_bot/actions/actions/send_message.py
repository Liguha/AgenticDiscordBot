from ..structs import ExecutionContext
from ..wrapper import Action

__all__ = ["send_message"]

@Action
async def send_message(ctx: ExecutionContext, state: None, msg: str) -> tuple[None, None]:
    text_ch = ctx.text_channel
    if text_ch is None:
        raise ValueError("No text channel was provided.")
    await text_ch.send(msg)
    return None, None
    