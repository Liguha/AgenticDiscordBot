from urllib.parse import urlparse, parse_qs, unquote, quote_plus
from urllib.request import Request, urlopen
from urllib.error import URLError, HTTPError
import re
from html import unescape
from html.parser import HTMLParser
from discord import Client
from ..wrapper import Action
from ...events import EventBroker
from ...return_types import WebSearchResult
from ...utils import run_in_executor

__all__ = ["search_web"]

DDG_LITE_URL: str = "https://lite.duckduckgo.com/lite/?q="
DDG_TIMEOUT: float = 15.0
PAGE_TIMEOUT: float = 15.0
USER_AGENT: str = "Mozilla/5.0"
PAGE_READ_LIMIT: int = 1_000_000
CONTENT_MAX_LEN: int = 2500
CONTENT_SEGMENTS: int = 6
MIN_SEGMENT_LEN: int = 12

_RESULT_ANCHOR = re.compile(r"<a rel=\"nofollow\" href=\"([^\"]+)\" class='result-link'>(.*?)</a>", re.S)
_RESULT_SNIPPET = re.compile(r"<td class='result-snippet'>(.*?)</td>", re.S)
_TAG_RE = re.compile(r"<[^>]+>")
_BOILERPLATE = re.compile(r"subscribe|newsletter|copyright|all rights reserved|follow us|share this|skip to|cookie policy", re.I)


def _clean_text(raw: str) -> str:
    return unescape(_TAG_RE.sub("", raw)).strip()


def _decode_link(fragment: str) -> str:
    query: list[str] = parse_qs(urlparse(fragment).query).get("uddg", [])
    return unquote(query[0]) if query else fragment


class _ParagraphExtractor(HTMLParser):
    """Collects plain text of <p> segments in document order."""

    def __init__(self) -> None:
        super().__init__()
        self._depth: int = 0
        self._buf: list[str] = []
        self.segments: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag == "p":
            self._depth += 1
        elif tag == "br":
            self._buf.append(" ")

    def handle_endtag(self, tag: str) -> None:
        if tag == "p":
            self._depth -= 1
            if self._depth == 0:
                text: str = re.sub(r"\s+", " ", "".join(self._buf)).strip()
                self._buf = []
                if text:
                    self.segments.append(text)

    def handle_data(self, data: str) -> None:
        if self._depth > 0:
            self._buf.append(data)


def _extract_content(html: str) -> str:
    parser = _ParagraphExtractor()
    parser.feed(html)
    segments: list[str] = []
    for segment in parser.segments:
        if _BOILERPLATE.search(segment):
            continue
        if len(segment) < MIN_SEGMENT_LEN:
            continue
        segments.append(segment)
    return "\n".join(segments[:CONTENT_SEGMENTS])[:CONTENT_MAX_LEN]


def _fetch_page_content(url: str) -> str:
    try:
        request = Request(url, headers={"User-Agent": USER_AGENT})
        with urlopen(request, timeout=PAGE_TIMEOUT) as response:
            html: str = response.read(PAGE_READ_LIMIT).decode("utf-8", "ignore")
    except (HTTPError, URLError, TimeoutError, OSError, ValueError):
        return ""
    return _extract_content(html)


@run_in_executor
def _search_full(query: str, limit: int) -> list[WebSearchResult]:
    request = Request(DDG_LITE_URL + quote_plus(query), headers={"User-Agent": USER_AGENT})
    try:
        with urlopen(request, timeout=DDG_TIMEOUT) as response:
            body: str = response.read().decode("utf-8", "ignore")
    except (HTTPError, URLError, TimeoutError, OSError):
        return []
    anchors = list(_RESULT_ANCHOR.finditer(body))[:limit]
    results: list[WebSearchResult] = []
    for i, match in enumerate(anchors):
        window_end = anchors[i + 1].start() if i + 1 < len(anchors) else len(body)
        window: str = body[match.end():window_end]
        snippet = _RESULT_SNIPPET.search(window)
        results.append(WebSearchResult(
            title=_clean_text(match.group(2)),
            link=_decode_link(match.group(1)),
            summary=_clean_text(snippet.group(1)) if snippet else None,
            content=""
        ))
    if results:
        results[0].content = _fetch_page_content(results[0].link)
    return results


@Action
async def search_web(broker: EventBroker, client: Client, state: None, query: str, limit: int = 3) -> tuple[list[WebSearchResult] | None, None]:
    results = await _search_full(query, max(1, limit))
    return results or None, None