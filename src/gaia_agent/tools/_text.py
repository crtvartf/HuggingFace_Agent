"""Helpers shared by tools that return long text."""

PAGE_CHARS = 20_000


def paginate(text: str, start: int = 0, size: int = PAGE_CHARS) -> str:
    """Return one window of `text`, with a note telling the agent how to read on."""
    start = max(start, 0)
    chunk = text[start : start + size]
    end = start + len(chunk)
    if end < len(text):
        chunk += f"\n\n[... showing chars {start}-{end} of {len(text)}; call again with start={end} to read on]"
    return chunk
