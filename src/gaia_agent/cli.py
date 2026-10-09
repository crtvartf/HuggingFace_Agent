"""`gaia` command line: fetch | doctor | ask | run | eval | submit."""

import argparse
import shutil
from datetime import datetime
from pathlib import Path

from gaia_agent.llm import tracker
from gaia_agent.settings import get_models_config, get_settings


def cmd_fetch(args: argparse.Namespace) -> None:
    from gaia_agent.scoring_api import fetch_tasks

    tasks = fetch_tasks(get_settings())
    expected = [t for t in tasks if t.file_name]
    got = [t for t in expected if t.file_path]
    print(f"Cached {len(tasks)} questions and {len(got)}/{len(expected)} files in {get_settings().tasks_dir}")
    for t in tasks:
        print(f"  {t.task_id[:8]}  {(t.file_name or '-'):>45}  {t.question[:70]!r}")


def cmd_doctor(args: argparse.Namespace) -> None:
    settings = get_settings()
    checks = {
        "OPENROUTER_API_KEY": bool(settings.openrouter_api_key),
        "TAVILY_API_KEY": bool(settings.tavily_api_key),
        "HF_TOKEN (task files + local eval)": bool(settings.hf_token),
        "HF_USERNAME (submit only)": bool(settings.hf_username),
        "AGENT_CODE_URL (submit only)": bool(settings.agent_code_url),
        "stockfish binary": bool(shutil.which("stockfish") or shutil.which("stockfish", path="/usr/games")),
        "tasks cached": (settings.tasks_dir / "questions.json").exists(),
        "phoenix tracing": bool(settings.phoenix_endpoint),
    }
    for name, ok in checks.items():
        print(f"  [{'ok' if ok else '--'}] {name}")
    models = get_models_config()
    print(
        f"\n  agent={models.agent.model}  vision={models.vision.model}  video={models.video.model}  "
        f"audio=faster-whisper:{models.audio.whisper_model}  budget=${settings.max_run_usd:.2f}/run"
    )


def _start(args: argparse.Namespace) -> None:
    from gaia_agent.tracing import setup_tracing

    settings = get_settings()
    tracker.limit_usd = args.max_usd if args.max_usd is not None else settings.max_run_usd
    if setup_tracing(settings):
        print(f"Tracing to Phoenix at {settings.phoenix_endpoint}")


def cmd_ask(args: argparse.Namespace) -> None:
    from gaia_agent.runner import run_task
    from gaia_agent.scoring_api import Task

    _start(args)
    file_path = Path(args.file) if args.file else None
    task = Task(task_id="adhoc", question=args.question, file_path=file_path)
    result = run_task(task, get_models_config())
    print(f"\n{result.state}: {result.answer}\n(raw: {result.raw_answer!r}, ${result.cost_usd:.4f})")


def cmd_run(args: argparse.Namespace) -> None:
    from gaia_agent.runner import run_tasks
    from gaia_agent.scoring_api import load_tasks

    _start(args)
    settings = get_settings()
    tasks = load_tasks(settings)
    if args.ids:
        tasks = [t for t in tasks if any(t.task_id.startswith(i) for i in args.ids)]
    if args.limit:
        tasks = tasks[: args.limit]
    name = args.name or datetime.now().strftime("%Y%m%d-%H%M%S")
    run_dir = settings.runs_dir / name
    print(f"Run '{name}': {len(tasks)} task(s), budget ${tracker.limit_usd:.2f} -> {run_dir}")
    results = run_tasks(tasks, get_models_config(), run_dir, rerun=args.rerun)
    answered = sum(1 for r in results if r.answer)
    print(f"\nDone: {answered}/{len(results)} answered, spent ${tracker.total_usd:.4f} this session.")
    print(f"Next: gaia eval {name}")


def _run_dir(name: str) -> Path:
    path = get_settings().runs_dir / name
    if not (path / "answers.jsonl").exists():
        raise SystemExit(f"No answers at {path}")
    return path


def cmd_eval(args: argparse.Namespace) -> None:
    from gaia_agent.answer import gaia_score, strict_score
    from gaia_agent.gold import load_gold
    from gaia_agent.runner import load_results, write_summary

    run_dir = _run_dir(args.run)
    gold = load_gold(get_settings())
    results = load_results(run_dir)
    rows, gaia_ok, strict_ok = [], 0, 0
    for r in results.values():
        truth = gold.get(r.task_id)
        if truth is None:
            continue
        g, s = gaia_score(r.answer, truth), strict_score(r.answer, truth)
        gaia_ok, strict_ok = gaia_ok + g, strict_ok + s
        rows.append(
            {
                "task_id": r.task_id,
                "ok": g,
                "strict": s,
                "answer": r.answer,
                "truth": truth,
                "state": r.state,
                "steps": r.steps,
                "cost_usd": round(r.cost_usd, 4),
            }
        )
        mark = "PASS" if g else "fail"
        print(f"  {mark}  {r.task_id[:8]}  got={r.answer!r:<40.40} want={truth!r:.40}  ${r.cost_usd:.3f}")
    n = len(rows)
    cost = sum(r.cost_usd for r in results.values())
    print(f"\nGAIA scorer: {gaia_ok}/{n} ({gaia_ok / max(n, 1):.0%})   strict: {strict_ok}/{n}   cost ${cost:.4f}")
    write_summary(run_dir, rows)


def cmd_submit(args: argparse.Namespace) -> None:
    from gaia_agent.runner import latest_answers
    from gaia_agent.scoring_api import Answer, ScoringAPI

    settings = get_settings()
    settings.require("hf_username", "agent_code_url")
    answers = [Answer(**a) for a in latest_answers(_run_dir(args.run))]
    print(f"Submitting {len(answers)} answers as '{settings.hf_username}', code: {settings.agent_code_url}")
    if not args.yes:
        raise SystemExit("Dry run. Re-run with --yes to actually submit to the course leaderboard.")
    result = ScoringAPI(settings.scoring_api_url).submit(settings.hf_username, settings.agent_code_url, answers)
    print(result)


def main() -> None:
    parser = argparse.ArgumentParser(prog="gaia", description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("fetch", help="download questions and attached files").set_defaults(func=cmd_fetch)
    sub.add_parser("doctor", help="check keys, binaries and config (no paid calls)").set_defaults(func=cmd_doctor)

    ask = sub.add_parser("ask", help="ask the agent an ad-hoc question")
    ask.add_argument("question")
    ask.add_argument("--file", help="optional attached file path")
    ask.add_argument("--max-usd", type=float)
    ask.set_defaults(func=cmd_ask)

    run = sub.add_parser("run", help="answer cached tasks")
    run.add_argument("--ids", nargs="*", help="task id prefixes to run (default: all)")
    run.add_argument("--limit", type=int)
    run.add_argument("--name", help="run directory name (reuse to resume)")
    run.add_argument("--rerun", action="store_true", help="re-answer tasks already in the run")
    run.add_argument("--max-usd", type=float, help="override MAX_RUN_USD for this run")
    run.set_defaults(func=cmd_run)

    ev = sub.add_parser("eval", help="score a run locally against GAIA gold answers")
    ev.add_argument("run")
    ev.set_defaults(func=cmd_eval)

    submit = sub.add_parser("submit", help="submit a run to the course scoring API")
    submit.add_argument("run")
    submit.add_argument("--yes", action="store_true", help="actually submit (default is a dry run)")
    submit.set_defaults(func=cmd_submit)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
