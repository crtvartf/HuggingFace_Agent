import httpx
import trafilatura
from smolagents import tool

from gaia_agent.tools._text import paginate
from gaia_agent.tools.search import _client as tavily_client

USER_AGENT = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0 Safari/537.36"


def _direct(url: str) -> str | None:
    response = httpx.get(url, headers={"User-Agent": USER_AGENT}, timeout=30, follow_redirects=True)
    response.raise_for_status()
    if "html" not in response.headers.get("content-type", "html"):
        return response.text
    return trafilatura.extract(
        response.text, output_format="markdown", include_tables=True, include_links=True, favor_recall=True
    )


def _tavily(url: str) -> str | None:
    result = tavily_client().extract(url, extract_depth="advanced", format="markdown")
    pages = result.get("results", [])
    return pages[0].get("raw_content") if pages else None


@tool
def fetch_page(url: str, start: int = 0) -> str:
    """Opens a web page and returns its main content as markdown (tables kept), 20k chars at a time.
    For Wikipedia articles prefer the wikipedia_page tool.

    Args:
        url: Full http(s) URL of the page.
        start: Character offset to read from, for long pages (use the value given in the previous output).
    """
    errors = []
    for fetch in (_direct, _tavily):
        try:
            text = fetch(url)
            if text and text.strip():
                return paginate(text, start)
        except Exception as e:  # fall through to the next fetcher
            errors.append(f"{fetch.__name__}: {e}")
    return f"Could not fetch {url}. " + " | ".join(errors)
