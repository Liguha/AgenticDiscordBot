import os
import asyncio
from dotenv import load_dotenv
from discord import Client, Intents
from .events import EVENT_BROKER, DiscrordEventProducer
from .routers import (
    StateManager, 
    DiscordCLIGuildRouter, 
    InteractionCommand,
    DiscordAgentGuildRouter,
    LLMSession,
)
from .routers.discord_agent.config import PROVIDER_BASE_URL
from .globals import SERIALIZATION_PERIOD

async def main() -> None:
    load_dotenv()
    ds_token = os.getenv("DISCORD_BOT_TOKEN")
    openai_token = os.getenv("OPENAI_API_KEY")
    LLMSession.set_api_key(openai_token, PROVIDER_BASE_URL)
    await EVENT_BROKER.start()
    state_manager = StateManager(SERIALIZATION_PERIOD)
    root_group = state_manager.group_state
    await state_manager.start()
    # Discord section
    intents = Intents.default()
    intents.message_content = True
    client = Client(intents=intents)
    await client.login(ds_token)
    await InteractionCommand.register_all(client)
    discord_producer = DiscrordEventProducer(client, EVENT_BROKER)
    await discord_producer.start()
    discord_cli_router = DiscordCLIGuildRouter(client, 
                                               EVENT_BROKER, 
                                               root_group[DiscordCLIGuildRouter.group_from_context()])
    await discord_cli_router.start()
    discord_agent_router = DiscordAgentGuildRouter(client, 
                                                   EVENT_BROKER, 
                                                   root_group[DiscordAgentGuildRouter.group_from_context()])
    await discord_agent_router.start()
    # run client
    await client.connect()

if __name__ == "__main__":
    asyncio.run(main())