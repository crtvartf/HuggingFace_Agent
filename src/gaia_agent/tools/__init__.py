from gaia_agent.tools.chess_engine import chess_best_move
from gaia_agent.tools.files import read_file, run_python_file
from gaia_agent.tools.media import look_at_image, transcribe_audio
from gaia_agent.tools.search import web_search
from gaia_agent.tools.web import fetch_page
from gaia_agent.tools.wikipedia import wikipedia_page, wikipedia_search
from gaia_agent.tools.youtube import youtube_transcript, youtube_video_qa

ALL_TOOLS = [
    web_search,
    fetch_page,
    wikipedia_search,
    wikipedia_page,
    youtube_transcript,
    youtube_video_qa,
    transcribe_audio,
    look_at_image,
    chess_best_move,
    read_file,
    run_python_file,
]
