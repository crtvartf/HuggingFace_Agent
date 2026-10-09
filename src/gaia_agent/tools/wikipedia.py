import httpx
from lxml import html as lxml_html
from markdownify import markdownify
from smolagents import tool

from gaia_agent.tools._text import paginate

API = "https://en.wikipedia.org/w/api.php"
HEADERS = {"User-Agent": "gaia-agent/0.1 (HF Agents Course study project; python-httpx)"}
NOISE = (
    ".mw-editsection, sup.reference, .reference, .navbox, .vertical-navbox, .metadata, .ambox, "
    ".hatnote, .mw-references-wrap, .reflist, style, script, .noprint, .sistersitebox"
)


def _api(**params) -> dict:
    response = httpx.get(API, params={"format": "json", "formatversion": 2, **params}, headers=HEADERS, timeout=30)
    response.raise_for_status()
    data = response.json()
    if "error" in data:
        raise ValueError(data["error"].get("info", str(data["error"])))
    return data


def _revision_as_of(title: str, as_of: str) -> int:
    stamp = as_of if "T" in as_of else f"{as_of}T23:59:59Z"
    data = _api(
        action="query",
        prop="revisions",
        titles=title,
        rvlimit=1,
        rvdir="older",
        rvstart=stamp,
        rvprop="ids|timestamp",
        redirects=1,
    )
    page = data["query"]["pages"][0]
    if "revisions" not in page:
        raise ValueError(f"No revision of '{title}' on or before {as_of}")
    return page["revisions"][0]["revid"]


def _to_markdown(page_html: str) -> str:
    tree = lxml_html.fromstring(page_html)
    for node in tree.cssselect(NOISE):
        node.drop_tree()
    return markdownify(lxml_html.tostring(tree, encoding="unicode"), heading_style="ATX", strip=["a", "img"])


@tool
def wikipedia_search(query: str) -> str:
    """Searches English Wikipedia and returns matching article titles with snippets.

    Args:
        query: Search terms.
    """
    hits = _api(action="query", list="search", srsearch=query, srlimit=8)["query"]["search"]
    if not hits:
        return f"No Wikipedia articles for: {query}"
    return "\n".join(f"- {h['title']}: {markdownify(h['snippet'], strip=['span'])}" for h in hits)


@tool
def wikipedia_page(title: str, as_of: str = "", section: str = "", start: int = 0) -> str:
    """Reads an English Wikipedia page as markdown, tables included. Can read an older revision,
    which matters when a question says e.g. "use the 2022 version of Wikipedia".
    Also works for non-article pages such as "Wikipedia:Featured article candidates/...", talk pages
    or "Wikipedia:Featured articles".

    Args:
        title: Exact page title, e.g. "Mercedes Sosa" or "Talk:Giganotosaurus".
        as_of: Optional date "YYYY-MM-DD"; returns the latest revision on or before that date.
        section: Optional section heading to return only that section, e.g. "Studio albums".
        start: Character offset for long pages (use the value given in the previous output).
    """
    params: dict = {"action": "parse", "prop": "text|sections", "redirects": 1, "disableeditsection": 1}
    if as_of:
        params["oldid"] = _revision_as_of(title, as_of)
    else:
        params["page"] = title
    if section:
        sections = _api(**{**params, "prop": "sections"})["parse"]["sections"]
        wanted = section.strip().lower()
        match = next((s for s in sections if s["line"].lower() == wanted), None) or next(
            (s for s in sections if wanted in s["line"].lower()), None
        )
        if match is None:
            names = ", ".join(s["line"] for s in sections)
            return f"No section '{section}'. Sections: {names}"
        params["section"] = match["index"]
    parsed = _api(**params)["parse"]
    header = f"# {parsed['title']}" + (f" (revision {parsed.get('revid')}, as of {as_of})" if as_of else "")
    return paginate(f"{header}\n\n{_to_markdown(parsed['text'])}", start)
