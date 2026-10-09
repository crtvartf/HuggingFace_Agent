# GAIA agent — HF Agents Course, Unit 4

A [smolagents](https://github.com/huggingface/smolagents) `CodeAgent` that answers the 20 GAIA Level 1 questions of the
[Hugging Face Agents Course](https://huggingface.co/learn/agents-course) final assignment. It runs locally in Docker,
calls models through [OpenRouter](https://openrouter.ai), searches with [Tavily](https://tavily.com), and traces every
step to [Arize Phoenix](https://github.com/Arize-ai/phoenix).

| Role | Model / tool |
|---|---|
| Agent (writes and runs Python) | `deepseek/deepseek-v4.1-flash` |
| Images, chess diagrams | `deepseek/deepseek-v4.1-flash` |
| YouTube videos | `google/gemini-2.5-flash-lite` (watches the URL directly) |
| Audio | `faster-whisper` (local, free) |
| Chess | Stockfish via `python-chess` |
| Web | Tavily search + page fetch (trafilatura, Tavily extract as fallback) |
| Wikipedia | MediaWiki API, including old revisions ("the 2022 version") |

Models are configured per role in [config/models.yaml](config/models.yaml).

## Setup

1. `cp .env.example .env` and fill in `OPENROUTER_API_KEY`, `TAVILY_API_KEY` and `HF_TOKEN`.
2. Accept the terms of the gated [GAIA dataset](https://huggingface.co/datasets/gaia-benchmark/GAIA) with the same HF
   account. The course API's `/files` endpoint currently returns 404, so attached files (image, audio, `.py`, `.xlsx`)
   come from the dataset, and local scoring uses its answers.
3. Build and start tracing:

```bash
docker compose build
docker compose up -d phoenix        # UI at http://localhost:6006
```

## Usage

```bash
docker compose run --rm agent doctor                 # keys, binaries, config; no paid calls
docker compose run --rm agent fetch                  # cache questions + files in data/tasks
docker compose run --rm agent run --ids 2d83 6f37    # a few tasks (id prefixes)
docker compose run --rm agent run --name full        # all 20; rerun the same --name to resume
docker compose run --rm agent eval full              # score locally against GAIA gold answers
docker compose run --rm agent ask "What is 2+2?"     # ad-hoc question
docker compose run --rm agent submit full            # dry run; add --yes to really submit
```

Each run writes `data/runs/<name>/answers.jsonl` (answer, raw answer, steps, tokens, cost, time per task) and
`eval.json` after scoring. A run stops when it has spent `MAX_RUN_USD` (default $2), or `--max-usd` for one run.

`src/` is mounted into the container, so code edits apply without rebuilding. Rebuild after changing dependencies.

## Development (host)

```bash
uv sync
uv run pytest
uv run ruff check src tests
```

## Notes

- The agent executes Python written by the LLM. The container is the sandbox: it runs as a non-root user and only
  `./data` is writable. API keys are in its environment, so don't add tools that expose them.
- GAIA asks that its answers are not republished: `data/` (gold answers, runs) is git-ignored.
- Submitting needs `HF_USERNAME` and `AGENT_CODE_URL` (the public URL of this repo) in `.env`.
