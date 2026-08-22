from pydantic import BaseModel, Field
from discord import Client, Guild
from .base import ToolResult, Tool, ToolError, ToolErrorCodes
from ....events import EventBroker
from ....actions import search_web

__all__ = ["WebSearchResultItem", "WebSearchResult", "web_search"]

GROUP_ID: str = "web"


class WebSearchResultItem(BaseModel):
    title: str = Field(description="The result title.")
    link: str = Field(description="The result URL.")
    summary: str | None = Field(description="Short snippet describing the result, or null when unavailable.")


class WebSearchResult(ToolResult):
    query: str = Field(description="The search query that produced these results.")
    answer: str | None = Field(description="Extracted text of the top page; use this to answer factual/dynamic questions (weather, news, stats) by quoting relevant facts from it.")
    top_link: str | None = Field(description="Link to the page the answer was extracted from.")
    results: list[WebSearchResultItem] = Field(description="Ordered top search results (title, link, summary).")


@Tool.with_group(GROUP_ID)
async def web_search(broker: EventBroker,
                     client: Client,
                     guild: Guild,
                     state: None,
                     query: str,
                     limit: int = 3
                    ) -> tuple[WebSearchResult | ToolError, None]:
    """Search the web and fetch the top page's content to answer factual or dynamic questions.

    Good for: weather, current events, facts, lists, figures — anything needing fresh
    information from the web. Returns the extracted top-page text so you can quote it,
    plus the ordered result list.

    Args:
        query: The question or keywords to search for.
        limit: How many top results to return alongside the answer.

    Returns:
        The extracted answer text, its source link, and ordered results.
    """
    results, _ = await search_web(broker, client, None, query, limit=limit)
    if not results:
        return ToolError(
            error_code=ToolErrorCodes.RUNTIME_ERROR.name,
            message="No web results were returned for the query."
        ), None
    top = results[0]
    answer: str | None = top.content or top.summary
    return WebSearchResult(
        query=query,
        answer=answer,
        top_link=top.link,
        results=[
            WebSearchResultItem(title=r.title, link=r.link, summary=r.summary)
            for r in results
        ]
    ), None