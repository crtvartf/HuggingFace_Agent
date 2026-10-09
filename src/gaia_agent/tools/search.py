from smolagents import tool
from tavily import TavilyClient

from gaia_agent.settings import get_settings


def _client() -> TavilyClient:
    settings = get_settings()
    settings.require("tavily_api_key")
    return TavilyClient(api_key=settings.tavily_api_key.get_secret_value())


@tool
def web_search(query: str, max_results: int = 6) -> str:
    """Searches the web (Tavily) and returns the top results: title, URL and a content snippet.
    Snippets are short and can be stale; open promising URLs with fetch_page before trusting a fact.

    Args:
        query: Specific search query. Include names, dates, sites or exact phrases when known.
        max_results: Number of results to return, between 1 and 10.
    """
    result = _client().search(query, search_depth="advanced", max_results=min(max(max_results, 1), 10))
    hits = result.get("results", [])
    if not hits:
        return f"No results for: {query}"
    return "\n\n".join(
        f"[{i}] {h.get('title', '')}\nURL: {h.get('url', '')}\n{h.get('content', '').strip()}"
        for i, h in enumerate(hits, 1)
    )
