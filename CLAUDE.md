# CLAUDE.md

## Project Overview

`llm-bug-bench` — Web-based benchmark suite evaluating LLMs' bug-detection ability. Supports Ollama (local), OpenAI, and Gemini providers. Measures detection accuracy via LLM judge scoring and speed via tok/s. Full web UI with HTMX + Tailwind CSS + dark mode. Source code lives in `src/`.

## Commands

```bash
# Start the web UI (main entry point)
poetry install
python -m src                          # default port 8080
python -m src --port 3000              # custom port
python -m src --results-dir ./results --tests-dir ./tests

# Make shortcuts
make serve PORT=8080
make build      # build Docker image
make clean      # delete results
make results    # print summary
make precommit  # run black formatter, mypy type checking and pylint static checking
```

If you want to run a bare command run it with the virtual env: "source .venv/bin/activate && cmd"

**CLI args:** `--port` (8080), `--results-dir` (./results), `--tests-dir` (./tests)

**Env vars:** `PORT`, `RESULTS_DIR`, `TESTS_DIR`, `OLLAMA_URL` (http://localhost:11434), `OPENAI_API_KEY`

## Architecture

```
__main__.py → web/app.py → web/routes/*.py
                          → core/runner.py → core/llm_client.py / core/loader.py / core/results.py
                          → core/judge.py
                          → core/ollama_manager.py
                          → core/leaderboard.py
```

| Package | Module | Purpose |
|---------|--------|---------|
| `core/` | `runner.py` | Core loop: load tests, query LLM, save JSON results |
| `core/` | `llm_client.py` | OpenAI SDK wrapper + Ollama native streaming + multi-provider factory |
| `core/` | `llm_protocol.py` | `LLMClientProtocol` for DI |
| `core/` | `judge.py` | LLM-based scoring (1-20 rubric) via OpenAI |
| `core/` | `loader.py` | YAML test discovery + CRUD (save/update/delete) |
| `core/` | `results.py` | JSON persistence at `results/<model>/run_NNN/` |
| `core/` | `ollama_manager.py` | Async Ollama REST API (list/pull/delete/show models) |
| `core/` | `leaderboard.py` | Aggregate scores across runs per model |
| `web/` | `app.py` | FastAPI app factory, DI setup |
| `web/` | `task_manager.py` | Background asyncio tasks with SSE progress queues |
| `web/` | `dependencies.py` | FastAPI `Depends` providers |
| `web/routes/` | `dashboard.py` | `GET /` main dashboard |
| `web/routes/` | `runs.py` | Run detail, new run form, SSE progress, delete |
| `web/routes/` | `tests.py` | Test CRUD routes |
| `web/routes/` | `ollama.py` | Ollama model management |
| `web/routes/` | `judge.py` | Trigger judging from UI with SSE progress |
| `web/routes/` | `leaderboard.py` | Sortable leaderboard |
| `web/routes/` | `export.py` | CSV/Markdown export |
| `web/routes/` | `compare.py` | Side-by-side run comparison |
| — | `models.py` | Frozen dataclasses: `TestCase`, `TestResult`, `RunMetadata`, `JudgeResult`, `OllamaModel`, `ProviderConfig`, `RunConfig`, `RunProgress`, `LeaderboardEntry` |
| — | `exceptions.py` | Domain exceptions |
| — | `metrics.py` | Computes tokens/second |

## Web UI Pages

| Path | Description |
|------|-------------|
| `/` | Dashboard: all runs with stats |
| `/leaderboard` | Sortable model leaderboard (score, speed, runs) |
| `/runs/new` | Start a run (Ollama/OpenAI/Gemini provider selector) |
| `/runs/progress/{task_id}` | SSE progress tracking |
| `/run/{model}/{run_id}` | Run detail with test results table |
| `/run/{model}/{run_id}/{test_id}` | Test result + judge evaluation |
| `/tests` | Test case browser with filters |
| `/tests/new` | Create test case |
| `/tests/{test_id}/edit` | Edit test case |
| `/tests/{test_id}` | View test case definition |
| `/ollama` | Model management (list/pull/delete) |
| `/compare` | Side-by-side run comparison |

## Test Cases

YAML files in `tests/`, auto-discovered. Fields: `id`, `title`, `language`, `difficulty`, `prompt`, `code` (optional), `expected_issues`, `notes`.

12 tests: 5 Go, 5 Python, 2 theory (CAP, Byzantine faults).

## Dependencies

Python 3.13+, Poetry, `openai`, `pyyaml`, `python-dotenv`, `fastapi`, `uvicorn`, `jinja2`, `httpx`, `python-multipart`.

---

## Collaboration Protocol

1. **Before coding**: Describe approach, wait for approval. Ask if requirements are ambiguous.
2. **After coding**: List what could break and which tests need adding.

## Code Style

- Early returns; functions <20 lines; one class per file.
- `handle_` prefix for event handlers; verb-noun naming.
- Immutable data: `frozen=True`, `slots=True` dataclasses.
- Fail fast: validate early, domain exceptions, no bare `except`.
- **Minimal changes**: only modify code directly related to the task.

## Design Principles

- **DI via constructor**: Pass deps through `__init__`. No hard-importing/instantiating clients internally.
- **Abstractions**: Depend on ABC or Protocol. Keep interfaces small.
- **Composition over inheritance**: Prefer has-a over is-a.

## Testing

- Test interfaces, not implementations.
- Use DI for easy mocking.
- Mock external services (LLM API) in unit tests.
- Use Protocol for lightweight test doubles.

## Resource Management

- Stream large files (generators); context managers for cleanup.
- Bounded buffers: limit concurrent ops.
- `asyncio.to_thread()` for blocking I/O in async context.
- Batch small operations; lazy evaluation for expensive computations.

## Anti-Patterns

- No god objects, circular deps, global mutable state
- No mixing business logic with infrastructure
- No unbounded concurrent task creation
- No catching `Exception` without re-raise
- No skipping resource cleanup in error paths
