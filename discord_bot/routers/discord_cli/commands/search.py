"""Search the web and return the top page's content plus matching links."""

import shlex
import re
from typing import Any
from functools import lru_cache
from argparse import ArgumentParser
from discord import Interaction, Message, Client
from discord.utils import escape_markdown, escape_mentions
from .base import InteractionCommand, MessageCommand
from ....events import EventBroker
from ....actions import search_web
from ....return_types import WebSearchResult

__all__ = ["message_search", "interaction_search"]

ARGS_DESC = {
    "query": "The question or keywords you want to look up.",
    "limit": "Number of top results to return alongside the answer (below 10)."
}

MAX_LIMIT: int = 8
DISCORD_MESSAGE_LIMIT: int = 1950

_MD_LINK_RE = re.compile(r"!?\[([^\]]*)\]\((https?://[^\s)]+)\)", re.I)
_BARE_URL_RE = re.compile(r"https?://[^\s<>)()]+", re.I)

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
        "limit": max(1, min(MAX_LIMIT, args.limit))
    }

def _render_link(match: re.Match[str]) -> str:
    label: str = match.group(1).strip()
    url: str = match.group(2)
    return f"{label} {url}".strip()


def _escape_content(text: str) -> str:
    text = re.sub(r"\n\s*\n+", "\n", text)
    text = _MD_LINK_RE.sub(_render_link, text)
    text = escape_markdown(escape_mentions(text))
    return _BARE_URL_RE.sub(lambda m: f"<{m.group(0)}>", text)


def _format_answer(results: list[WebSearchResult] | None) -> str:
    if not results:
        return "No results found for your query."
    blocks: list[str] = []
    total: int = 0
    for idx, result in enumerate(results, start=1):
        block = (
            f"**{idx}. {_escape_content(result.title)}**"
            f"🔗 {_escape_content(result.link)}\n"
            f"{_escape_content(result.content)}"
        )
        if total + len(block) > DISCORD_MESSAGE_LIMIT:
            break
        blocks.append(block)
        total += len(block)
    omitted: int = len(results) - len(blocks)
    text = "\n\n".join(blocks)
    if omitted:
        text += f"\n\n... and {omitted} more (use --limit for more)."
    return text

@MessageCommand.add_parsers(
    query=lambda token, client, msg: parse_search_flags(msg.content)["query"],
    limit=lambda token, client, msg: parse_search_flags(msg.content)["limit"]
)
@MessageCommand.add_descriptions(**ARGS_DESC)
@MessageCommand.with_name("search")
async def message_search(broker: EventBroker, client: Client, message: Message, state: None, query: str, limit: int = 3) -> None:
    results, _ = await search_web(broker, client, None, query, limit=limit, mode="hybrid", search_type="auto")
    await message.reply(_format_answer(results))

@InteractionCommand.add_descriptions(**ARGS_DESC)
@InteractionCommand.with_name("search")
async def interaction_search(broker: EventBroker, interaction: Interaction, state: None, query: str, limit: InteractionCommand.Range[int, 1, MAX_LIMIT] = 3) -> None:
    results, _ = await search_web(broker, interaction.client, None, query, limit=limit, mode="hybrid", search_type="auto")
    await interaction.followup.send(_format_answer(results))