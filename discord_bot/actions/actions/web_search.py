import os
import re
from typing import Literal
from exa_py import Exa
from exa_py.api import Result
from discord import Client
from ..wrapper import Action
from ...events import EventBroker
from ...return_types import WebSearchResult
from ...utils import run_in_executor

__all__ = ["search_web", "SearchMode", "SearchType"]

type SearchMode = Literal["highlights", "hybrid"]
type SearchType = Literal["instant", "fast", "auto"]

DEFAULT_MODE: SearchMode = "highlights"
DEFAULT_TYPE: SearchType = "auto"
MAX_NUM_RESULTS: int = 8
DEFAULT_NUM_RESULTS: int = 3
CONTENT_MAX_LEN: int = 500

_EXA: Exa | None = None

def _clamp_num_results(n: int) -> int:
    return max(1, min(n, MAX_NUM_RESULTS))

def _exa() -> Exa:
    global _EXA
    if _EXA is None:
        key = os.getenv("EXA_API_KEY")
        if not key:
            raise RuntimeError("Exa API key missing: set EXA_API_KEY in .env")
        _EXA = Exa(api_key=key)
    return _EXA

def _shorten(text: str, max_chars: int) -> str:
    lines: list[str] = []
    for raw_line in text.splitlines():
        line = re.sub(r"\s*\.\.\.\s*", " ", re.sub(r"\s+", " ", raw_line.strip()))
        if line:
            lines.append(line)
    out = "\n".join(lines)
    if len(out) > max_chars:
        out = out[:max_chars].rstrip()
        if not out.endswith(("…", ".", "!", "?")):
            out += "…"
    return out

def _excerpt_of(result: Result, max_chars: int) -> str:
    raw = " ".join(result.highlights or []).strip() if result.highlights else (result.text or "")
    return _shorten(raw, max_chars)

def _summary_of(result: Result, max_chars: int) -> str:
    raw = result.summary or result.text or ""
    return _shorten(raw, max_chars)

def _build_results(query: str, limit: int, mode: SearchMode, search_type: SearchType) -> list[WebSearchResult]:
    n = _clamp_num_results(limit)
    exa = _exa()
    res = exa.search(
        query,
        type=search_type,
        num_results=n,
        contents={"highlights": True, "max_age_hours": -1},
    )
    results: list[WebSearchResult] = []
    for idx, item in enumerate(res.results or []):
        if mode == "hybrid" and idx == 0:
            contents = exa.get_contents([item.url], summary={"query": query}, max_age_hours=-1)
            best = contents.results[0] if contents.results else item
            content = _summary_of(best, CONTENT_MAX_LEN)
        else:
            content = _excerpt_of(item, CONTENT_MAX_LEN)
        results.append(WebSearchResult(
            title=item.title or "",
            link=item.url or "",
            content=content,
        ))
    return results

@run_in_executor
def _build_results_async(query: str, limit: int, mode: SearchMode, search_type: SearchType) -> list[WebSearchResult]:
    return _build_results(query, limit, mode, search_type)

@Action
async def search_web(broker: EventBroker,
                     client: Client,
                     state: None,
                     query: str,
                     limit: int = DEFAULT_NUM_RESULTS,
                     mode: SearchMode = DEFAULT_MODE,
                     search_type: SearchType = DEFAULT_TYPE
                    ) -> tuple[list[WebSearchResult] | None, None]:
    """Search the web via Exa and return ranked results with content excerpts.

    `mode` selects the result shaping: "highlights" (fast, every result a raw
    excerpt) or "hybrid" (slower, the top result summarized via an extra
    `/contents` call, the rest excerpts). `search_type` picks the Exa search
    type; only "instant" | "fast" | "auto" are allowed. `limit` is capped below
    10 to keep the flat base cost.
    """
    try:
        results = await _build_results_async(query, limit, mode, search_type)
    except Exception:
        return None, None
    return results or None, None