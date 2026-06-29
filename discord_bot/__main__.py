import os
import asyncio
from collections.abc import Coroutine
from asyncio import gather
from dotenv import load_dotenv
from discord import Client, Intents
from .events import EVENT_BROKER, DiscrordEventProducer
from .routers import StateManager, DiscordCLIRouter
from .globals import SERIALIZATION_PERIOD

async def main() -> None:
    load_dotenv()
    ds_token = os.getenv("DISCORD_BOT_TOKEN")
    await EVENT_BROKER.start()
    state_manager = StateManager(SERIALIZATION_PERIOD)
    root_group = state_manager.group_state
    await state_manager.start()
    # Discord section
    intents = Intents.default()
    intents.message_content = True
    client = Client(intents=intents)
    await client.login(ds_token)
    discord_producer = DiscrordEventProducer(client, EVENT_BROKER)
    await discord_producer.start()
    discord_cli_router = DiscordCLIRouter(client, EVENT_BROKER, root_group)
    await discord_cli_router.start()
    await client.connect()

if __name__ == "__main__":
    asyncio.run(main())