import re

from smolagents import tool
from youtube_transcript_api import YouTubeTranscriptApi

from gaia_agent.llm import chat
from gaia_agent.settings import get_models_config

VIDEO_SYSTEM = (
    "You watch videos carefully and answer questions about them precisely. "
    "When counting, scan the whole video and report the maximum seen at one moment if asked. "
    "Quote speech verbatim when asked what someone says. State uncertainty briefly if any."
)


def _video_id(url: str) -> str:
    match = re.search(r"(?:v=|youtu\.be/|shorts/|embed/)([\w-]{11})", url)
    if not match:
        raise ValueError(f"Not a YouTube URL: {url}")
    return match.group(1)


@tool
def youtube_transcript(url: str) -> str:
    """Returns the spoken transcript of a YouTube video with [mm:ss] timestamps.
    Cheapest way to answer questions about what is said in a video.

    Args:
        url: YouTube video URL.
    """
    try:
        fetched = YouTubeTranscriptApi().fetch(_video_id(url), languages=("en", "en-US", "en-GB"))
    except Exception as e:
        return f"No transcript available ({type(e).__name__}: {e}). Try youtube_video_qa instead."
    return "\n".join(f"[{int(s.start) // 60:02d}:{int(s.start) % 60:02d}] {s.text}" for s in fetched)


@tool
def youtube_video_qa(url: str, question: str) -> str:
    """Asks a video-capable model (it watches frames and hears audio) a question about a YouTube video.
    Use for visual questions, e.g. counting things on screen. Ask one precise question per call.

    Args:
        url: YouTube video URL.
        question: A precise, self-contained question about the video content.
    """
    role = get_models_config().video
    content = [
        {"type": "video_url", "video_url": {"url": f"https://www.youtube.com/watch?v={_video_id(url)}"}},
        {"type": "text", "text": question},
    ]
    return chat(role, content, system=VIDEO_SYSTEM)
