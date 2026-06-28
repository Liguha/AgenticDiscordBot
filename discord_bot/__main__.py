import os
import asyncio
from collections.abc import Coroutine
from asyncio import gather
from dotenv import load_dotenv
from discord import Client, Intents
from .events import EVENT_BROKER, DiscrordEventProducer
from .routers import DiscordCLIRouter

async def main() -> None:
    load_dotenv()
    ds_token = os.getenv("DISCORD_BOT_TOKEN")
    await EVENT_BROKER.start()
    # Discord section
    intents = Intents.default()
    intents.message_content = True
    client = Client(intents=intents)
    await client.login(ds_token)
    discord_producer = DiscrordEventProducer(client, EVENT_BROKER)
    await discord_producer.start()
    guilds = client.fetch_guilds()
    discord_cli_routers = [DiscordCLIRouter(client, g, EVENT_BROKER) async for g in guilds]
    await gather(*[r.start() for r in discord_cli_routers])
    await client.connect()

if __name__ == "__main__":
    asyncio.run(main())