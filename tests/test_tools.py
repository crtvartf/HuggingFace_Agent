import shutil

import pandas as pd
import pytest

from gaia_agent.tools import ALL_TOOLS, chess_best_move, read_file, run_python_file
from gaia_agent.tools._text import paginate


def test_tools_have_unique_names_and_descriptions():
    names = [t.name for t in ALL_TOOLS]
    assert len(names) == len(set(names))
    assert all(t.description for t in ALL_TOOLS)


def test_paginate_points_to_next_offset():
    out = paginate("x" * 50, start=0, size=20)
    assert "start=20" in out


def test_read_file_spreadsheet(tmp_path):
    path = tmp_path / "sales.xlsx"
    pd.DataFrame({"item": ["Burger", "Soda"], "sales": [10.5, 2.0]}).to_excel(path, index=False)
    out = read_file(str(path))
    assert "Burger" in out and "10.5" in out


def test_run_python_file(tmp_path):
    script = tmp_path / "s.py"
    script.write_text("print(6 * 7)\n")
    assert "42" in run_python_file(str(script))


@pytest.mark.skipif(
    not shutil.which("stockfish") and not shutil.which("stockfish", path="/usr/games"), reason="stockfish not installed"
)
def test_chess_finds_mate_in_one():
    # Black to move, Qh4# (fool's mate)
    fen = "rnbqkbnr/pppp1ppp/8/4p3/6P1/5P2/PPPPP2P/RNBQKBNR b KQkq - 0 2"
    out = chess_best_move(fen, think_seconds=1)
    assert "Qh4#" in out


def test_chess_rejects_bad_fen():
    assert chess_best_move("not a fen").startswith("Invalid FEN")
