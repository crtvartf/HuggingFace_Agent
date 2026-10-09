# GAIA agent: plan and status

Goal: answer the 20 GAIA Level 1 questions from Unit 4 of the HF Agents Course. Score above 30% for the certificate; stretch goal 60%+.
The user claims the Unit 1 and Unit 4 certificates themselves. This repo provides `gaia submit`.

## Decisions (2026-10-09)

| Area | Choice | Why |
|---|---|---|
| Runtime | Docker Compose on the local machine; public code on a separate GitHub account | The scoring API needs a public `agent_code` URL |
| Stack | Python 3.12, uv, smolagents `CodeAgent`, pydantic and pydantic-settings, Arize Phoenix | Same framework as the course; the loop is small and readable; code actions suit GAIA |
| LLM access | OpenRouter, through smolagents `OpenAIModel` (no LiteLLM) | One key; fewer dependencies. LiteLLM had compromised PyPI releases in March 2026 |
| Agent + vision | `deepseek/deepseek-v4.1-flash` | User's choice. Text and images, supports tools |
| Video | `google/gemini-2.5-flash-lite`, pinned to the `google-ai-studio` provider | Only AI Studio accepts YouTube URLs directly |
| Audio | local `faster-whisper` (small, int8, CPU) | Free and offline |
| Search | Tavily with its own key | User's choice |

Alternatives considered and not chosen: Pydantic AI (runner-up), OpenAI Agents SDK, Strands, LangGraph, Agno, Google ADK.

## Known issues

- The course API `/files/{task_id}` returns 404 for every task ("No file path associated with task_id").
  `gaia fetch` downloads these files from the gated `gaia-benchmark/GAIA` dataset instead, so it needs `HF_TOKEN` and accepted dataset terms.
- `av` 19 removed the `metadata_errors` argument that `faster-whisper` 1.2.1 passes, which silently broke transcription. `av` is pinned to `<19`, and a test guards it.
- The chess question fails: the vision model misreads the board (orientation, piece colours) and the agent runs out of steps. This is the M3 target.
- When a task hits `max_steps`, smolagents' fallback answer can be junk (a code fragment). Treat it as unanswered.

## Milestones

| # | Milestone | Status |
|---|---|---|
| M0 | Scaffold: repo, Docker, config, scoring API client, `gaia fetch` / `doctor` | done |
| M1 | Agent + tools (search, fetch, Wikipedia with revisions, YouTube, audio, vision, chess, files), answer normaliser, GAIA scorer port, `run` / `eval` / `submit` | done |
| M2 | First live runs: smoke-test 3–4 tasks, then all 20; read the Phoenix traces | done: run `full-v1` scored **19/20 (95%)** locally, ~$0.16 |
| M3 | Iterate on failures: prompts, tools, a dedicated image → FEN step for chess, planning interval, retries | |
| M4 | Push to a public GitHub repo; set `AGENT_CODE_URL`; `gaia submit --yes` | done: official score **19/20 (95%)** on 2026-10-09 (run `full-v1`) |

## Question → route

| Question type | Count | Route |
|---|---|---|
| Web / Wikipedia facts | 11 | `web_search`, `fetch_page`, `wikipedia_page(as_of=...)` |
| YouTube | 2 | `youtube_transcript` (speech), `youtube_video_qa` (visual counting) |
| Audio (mp3) | 2 | `transcribe_audio` |
| Chess image | 1 | `look_at_image` → FEN → `chess_best_move` |
| Excel / Python file | 2 | `read_file` or pandas in code; `run_python_file` |
| Pure reasoning (reversed text, operation table, botany list) | 3 | Python in the agent loop; no tools needed |
