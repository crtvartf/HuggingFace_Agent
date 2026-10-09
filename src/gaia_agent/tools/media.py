import base64
import mimetypes
from functools import lru_cache
from pathlib import Path

from smolagents import tool

from gaia_agent.llm import chat
from gaia_agent.settings import get_models_config, get_settings

VISION_SYSTEM = (
    "You inspect images with great care and answer precisely. Read text and numbers exactly. "
    "For chess diagrams, read every square rank by rank, note board orientation from the coordinate "
    "labels, and give a FEN when asked."
)


@lru_cache
def _whisper():
    from faster_whisper import WhisperModel  # heavy import, load on first use

    cfg = get_models_config().audio
    return WhisperModel(
        cfg.whisper_model,
        device=cfg.device,
        compute_type=cfg.compute_type,
        download_root=str(get_settings().data_dir / "models" / "whisper"),
    )


@tool
def transcribe_audio(file_path: str) -> str:
    """Transcribes speech in a local audio file (mp3, wav, m4a, ...) to text, locally with Whisper.

    Args:
        file_path: Path to the audio file.
    """
    segments, info = _whisper().transcribe(file_path, beam_size=5, vad_filter=True)
    text = " ".join(s.text.strip() for s in segments)
    return f"[language: {info.language}] {text}"


@tool
def look_at_image(file_path: str, question: str) -> str:
    """Asks a vision model a question about a local image file (png, jpg, webp, gif).
    Ask precise questions; for chess positions ask for the full FEN including side to move.

    Args:
        file_path: Path to the image file.
        question: What to find out about the image.
    """
    path = Path(file_path)
    mime = mimetypes.guess_type(path.name)[0] or "image/png"
    data_url = f"data:{mime};base64,{base64.b64encode(path.read_bytes()).decode()}"
    content = [
        {"type": "image_url", "image_url": {"url": data_url}},
        {"type": "text", "text": question},
    ]
    return chat(get_models_config().vision, content, system=VISION_SYSTEM)
