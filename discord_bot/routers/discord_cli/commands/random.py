"""Pick a random integer in range [lower;upper]."""

from random import randint
from discord import app_commands, Interaction, Message, Client
from .base import MessageCommand, InteractionCommand
from ....events import EventBroker

__all__ = ["message_random", "interaction_random"]

ARGS_DESC = {
    "lower": "The minimum integer",
    "upper": "The maximum integer"
}

@MessageCommand.add_descriptions(**ARGS_DESC)
@MessageCommand.with_name("random")
async def message_random(broker: EventBroker, client: Client, message: Message, state: None, lower: int, upper: int) -> None:
    number = randint(lower, upper)
    await message.reply(f"Your number is **{number}**")

@app_commands.describe(**ARGS_DESC)
@InteractionCommand.with_name("random")
async def interaction_random(broker: EventBroker, interaction: Interaction, state: None, lower: int, upper: int) -> None:
    number = randint(lower, upper)
    await interaction.followup.send(f"Your number is **{number}**")
