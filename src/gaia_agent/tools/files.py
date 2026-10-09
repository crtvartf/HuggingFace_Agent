import subprocess
import sys
from pathlib import Path

import pandas as pd
from pypdf import PdfReader
from smolagents import tool

from gaia_agent.tools._text import paginate

AUDIO = {".mp3", ".wav", ".m4a", ".flac", ".ogg"}
IMAGES = {".png", ".jpg", ".jpeg", ".webp", ".gif", ".bmp"}


def _spreadsheet(path: Path) -> str:
    sheets = pd.read_excel(path, sheet_name=None)
    parts = []
    for name, df in sheets.items():
        parts.append(f"## Sheet: {name} ({df.shape[0]} rows x {df.shape[1]} cols)\n{df.to_markdown(index=False)}")
    return "\n\n".join(parts)


@tool
def read_file(file_path: str, start: int = 0) -> str:
    """Reads a local file and returns its content as text: spreadsheets (xlsx/xls/csv) as markdown tables,
    PDFs as text, code and text files verbatim. For exact arithmetic over spreadsheets, load them with
    pandas in your own code instead of reading the table by eye.

    Args:
        file_path: Path to the file.
        start: Character offset for long files (use the value given in the previous output).
    """
    path = Path(file_path)
    if not path.exists():
        return f"File not found: {file_path}"
    suffix = path.suffix.lower()
    if suffix in AUDIO:
        return "This is an audio file; use transcribe_audio."
    if suffix in IMAGES:
        return "This is an image; use look_at_image."
    if suffix in {".xlsx", ".xls"}:
        text = _spreadsheet(path)
    elif suffix == ".csv":
        text = pd.read_csv(path).to_markdown(index=False)
    elif suffix == ".pdf":
        text = "\n\n".join(page.extract_text() or "" for page in PdfReader(path).pages)
    else:
        text = path.read_text(errors="replace")
    return paginate(text, start)


@tool
def run_python_file(file_path: str, timeout_seconds: int = 60) -> str:
    """Executes a local Python script in a subprocess and returns its stdout and stderr.
    Use for questions about the output of an attached .py file.

    Args:
        file_path: Path to the .py file.
        timeout_seconds: Kill the script after this many seconds (max 300).
    """
    path = Path(file_path).resolve()
    if not path.is_file():
        return f"File not found: {file_path}"
    try:
        done = subprocess.run(
            [sys.executable, path.name],
            cwd=path.parent,
            capture_output=True,
            text=True,
            timeout=min(max(timeout_seconds, 1), 300),
        )
    except subprocess.TimeoutExpired as e:
        return f"Timed out after {e.timeout}s. Partial stdout:\n{e.stdout or ''}"
    return f"exit code: {done.returncode}\n--- stdout ---\n{done.stdout}\n--- stderr ---\n{done.stderr}"
