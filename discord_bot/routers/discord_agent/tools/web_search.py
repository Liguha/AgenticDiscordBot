from pydantic import BaseModel, Field
from discord import Client, Guild
from .base import ToolResult, Tool, ToolError, ToolErrorCodes
from ....events import EventBroker
from ....actions import search_web

__all__ = ["WebSearchResultItem", "WebSearchResult", "web_search"]

class WebSearchResultItem(BaseModel):
    title: str = Field(description="The result title.")
    link: str = Field(description="The result URL.")
    summary: str = Field(description="Extracted content excerpt of the result.")

class WebSearchResult(ToolResult):
    results: list[WebSearchResultItem] = Field(description="Ordered search results, each with title, link, and a content excerpt.")

@Tool
async def web_search(broker: EventBroker,
                     client: Client,
                     guild: Guild,
                     state: None,
                     query: str,
                     limit: int = 3
                    ) -> tuple[WebSearchResult | ToolError, None]:
    """Search the web and return ranked results, each with a content excerpt, to answer factual or dynamic questions.

    Good for: weather, current events, facts, lists, figures — anything needing fresh
    information from the web. Every result carries an excerpt of its page text; quote
    the relevant facts from the excerpts to answer the user.

    Args:
        query: The question or keywords to search for.
        limit: How many top results to return (below 10).

    Returns:
        Ordered results, each with title, link, and a content excerpt.
    """
    results, _ = await search_web(broker, client, None, query, limit=limit, mode="highlights", search_type="fast")
    if not results:
        return ToolError(
            error_code=ToolErrorCodes.RUNTIME_ERROR.name,
            message="No web results were returned for the query."
        ), None
    return WebSearchResult(
        results=[WebSearchResultItem(title=r.title, link=r.link, summary=r.content) for r in results]
    ), None