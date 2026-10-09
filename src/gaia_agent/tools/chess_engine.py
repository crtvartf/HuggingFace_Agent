import shutil

import chess
import chess.engine
from smolagents import tool


def _stockfish_path() -> str:
    path = shutil.which("stockfish") or shutil.which("stockfish", path="/usr/games")
    if not path:
        raise RuntimeError("Stockfish is not installed (apt install stockfish).")
    return path


@tool
def chess_best_move(fen: str, think_seconds: float = 3.0) -> str:
    """Analyses a chess position with Stockfish and returns the best moves (SAN and UCI) with evaluations.
    Validate the FEN against the image first: piece placement, side to move, castling rights.

    Args:
        fen: Position in FEN, e.g. "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1".
        think_seconds: Engine thinking time per position, 1-10 seconds.
    """
    try:
        board = chess.Board(fen)
    except ValueError as e:
        return f"Invalid FEN: {e}"
    if not board.is_valid():
        return f"FEN parses but the position is illegal: {board.status()!r}"
    with chess.engine.SimpleEngine.popen_uci(_stockfish_path()) as engine:
        infos = engine.analyse(board, chess.engine.Limit(time=min(max(think_seconds, 1.0), 10.0)), multipv=3)
    lines = [f"Side to move: {'white' if board.turn else 'black'}"]
    for i, info in enumerate(infos, 1):
        pv = info.get("pv", [])
        if not pv:
            continue
        score = info["score"].pov(board.turn)
        evaluation = f"mate in {score.mate()}" if score.is_mate() else f"{score.score() / 100:+.2f}"
        line_san = board.variation_san(pv[:6])
        lines.append(f"{i}. {board.san(pv[0])} (uci {pv[0].uci()}), eval {evaluation}, line: {line_san}")
    return "\n".join(lines)
