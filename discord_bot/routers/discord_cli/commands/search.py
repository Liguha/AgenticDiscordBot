"""Search the web and return the top page's content plus matching links."""

import shlex
from typing import Any
from functools import lru_cache
from argparse import ArgumentParser
from discord import app_commands, Interaction, Message, Client
from .base import MessageCommand, InteractionCommand
from ....events import EventBroker
from ....actions import search_web

__all__ = ["message_search", "interaction_search"]

ARGS_DESC = {
    "query": "The question or keywords you want to look up.",
    "limit": "Number of top results to return alongside the answer."
}


@lru_cache(maxsize=1)
def parse_search_flags(message_content: str) -> dict[str, Any]:
    parts = message_content.split(maxsplit=1)
    tokens = shlex.split(parts[1]) if len(parts) > 1 else []
    parser = ArgumentParser()
    parser.add_argument("query", nargs="*")
    parser.add_argument("--limit", "-l", type=int, default=3)
    args, _ = parser.parse_known_args(tokens)
    return {
        "query": " ".join(args.query),
        "limit": args.limit
    }


def _format_answer(results) -> str:
    if not results:
        return "No results found for your query."
    top = results[0]
    lines = [f"**{top.title}**"]
    answer = top.content or ""
    if answer:
        lines.append(answer)
    lines.append(f"🔗 <{top.link}>")
    for idx, result in enumerate(results[1:], start=2):
        lines.append(f"\n**{idx}.** {result.title}\n<{result.link}>")
    return "\n".join(lines)


@MessageCommand.add_parsers(
    query=lambda token, client, msg: parse_search_flags(msg.content)["query"],
    limit=lambda token, client, msg: parse_search_flags(msg.content)["limit"]
)
@MessageCommand.add_descriptions(**ARGS_DESC)
@MessageCommand.with_name("search")
async def message_search(broker: EventBroker, client: Client, message: Message, state: None, query: str, limit: int = 3) -> None:
    results, _ = await search_web(broker, client, None, query, limit=limit)
    await message.reply(_format_answer(results))


@app_commands.describe(**ARGS_DESC)
@InteractionCommand.with_name("search")
async def interaction_search(broker: EventBroker, interaction: Interaction, state: None, query: str, limit: int = 3) -> None:
    results, _ = await search_web(broker, interaction.client, None, query, limit=limit)
    await interaction.followup.send(_format_answer(results))