# llm-bug-bench

A web-based benchmark suite that evaluates LLMs' ability to detect bugs in code. Focused on concurrency issues, error handling, and distributed systems patterns in Go and Python, plus theoretical questions (CAP theorem, Byzantine faults).

Supports **Ollama** (local models), **OpenAI**, and **Google Gemini** as providers. Includes an LLM judge that automatically scores responses on a 1–20 rubric, a sortable leaderboard, and full test case management — all through a web UI.

## Features

- **Multi-provider support** — run benchmarks against Ollama, OpenAI, or Gemini from a single interface
- **Ollama model management** — pull, list, and delete models directly from the UI
- **LLM judge scoring** — automated evaluation with a 1–20 rubric using an OpenAI judge model
- **Sortable leaderboard** — compare models by score, speed (tok/s), and number of runs
- **Test case CRUD** — create, edit, and delete YAML test cases from the browser
- **Run comparison** — side-by-side per-test scoring between any two runs
- **Export** — download results as CSV or Markdown
- **Dark mode** — toggle with system preference detection
- **Real-time progress** — SSE streaming for run execution and judge scoring

## Quick Start

### Prerequisites

- Python 3.13+
- [Poetry](https://python-poetry.org/)
- [Ollama](https://ollama.com) running locally (for local models)

### Install and run

```bash
git clone <repo-url> && cd llm-bug-bench
poetry install
make serve
```

Open [http://localhost:8080](http://localhost:8080) in your browser.

## Makefile Reference

| Target          | Description                              |
| --------------- | ---------------------------------------- |
| `make serve`    | Start the web UI (default port 8080)     |
| `make build`    | Build the Docker image                   |
| `make clean`    | Delete all results                       |
| `make results`  | Print a summary of all saved runs        |
| `make precommit`| Run formatters and linters               |

Variables (override on the command line):

| Variable       | Default      | Description              |
| -------------- | ------------ | ------------------------ |
| `PORT`         | `8080`       | Web server port          |
| `RESULTS_DIR`  | `./results`  | Results output directory |
| `BENCHMARKS_DIR`| `./benchmarks`| YAML benchmark cases directory|

## Configuration

### Environment variables

| Variable         | Default                    | Description                                |
| ---------------- | -------------------------- | ------------------------------------------ |
| `PORT`           | `8080`                     | Web server port                            |
| `RESULTS_DIR`    | `./results`                | Results output directory                   |
| `BENCHMARKS_DIR` | `./benchmarks`             | YAML benchmark cases directory             |
| `OLLAMA_URL`     | `http://localhost:11434`   | Ollama API base URL (overridable in the UI)|
| `OPENAI_API_KEY` | —                          | Required for LLM judge scoring             |

### CLI arguments

```
python -m src [OPTIONS]
```

| Argument        | Default              | Description                 |
| --------------- | -------------------- | --------------------------- |
| `--port`        | `8080` / `$PORT`     | Web server port             |
| `--results-dir` | `./results`          | Results output directory    |
| `--benchmarks-dir`| `./benchmarks`     | YAML benchmark cases directory|
| `--debug`       | off                  | Enable debug-level logging  |

## Web UI Guide

| Page                     | URL                                         | Description                                    |
| ------------------------ | ------------------------------------------- | ---------------------------------------------- |
| Dashboard                | `/`                                         | All runs with stats and average scores         |
| Leaderboard              | `/leaderboard`                              | Sortable model ranking by score, speed, runs   |
| New Run                  | `/runs/new`                                 | Configure and start a benchmark run            |
| Run Detail               | `/run/{model}/{run_id}`                     | Per-test results table with scores             |
| Test Detail              | `/run/{model}/{run_id}/{test_id}`           | Prompt, response, and judge evaluation         |
| Test Cases               | `/tests`                                    | Browse, filter, create, edit, delete tests     |
| Ollama Models            | `/ollama`                                   | Pull, list, and delete Ollama models           |
| Compare                  | `/compare`                                  | Side-by-side run comparison                    |

## Providers

All provider configuration is done through the **New Run** page (`/runs/new`).

### Ollama (local)

Select "Ollama" as the provider, enter the model name (e.g., `llama3:8b`), and optionally change the Ollama URL. The URL defaults to `OLLAMA_URL` env var or `http://localhost:11434`.

### OpenAI

Select "OpenAI", enter your model name (e.g., `gpt-4o`) and API key. The key is used only for the duration of the run and is never stored on disk.

### Google Gemini

Select "Gemini", enter your model name (e.g., `gemini-2.5-flash`) and API key. Uses the Gemini OpenAI-compatible endpoint.

## LLM Judge

The judge uses an OpenAI model (default: `gpt-5.2-chat-latest`) to score LLM responses against expected issues on a 1–20 rubric:

| Score   | Meaning                                                  |
| ------- | -------------------------------------------------------- |
| 17–20   | All issues found with precise root cause and consequence |
| 13–16   | Most issues found, minor gaps                            |
| 9–12    | Some issues found, significant gaps                      |
| 5–8     | Few issues found, or vague explanations                  |
| 1–4     | Issues missed, wrong analysis, or hallucinated bugs      |

### Requirements

Set `OPENAI_API_KEY` as an environment variable, or provide it per-request through the judge modal in the UI.

### Usage

1. Navigate to a run detail page (`/run/{model}/{run_id}`)
2. Click **Judge All**
3. Enter your API key (optional if env var is set) and judge model
4. Watch the progress bar as each test is scored

## Test Suite

The suite ships with 12 test cases across three categories:

### Go (5 tests)

| ID                | Title                                     | Difficulty |
| ----------------- | ----------------------------------------- | ---------- |
| `go_race_001`     | Race condition in concurrent counter      | easy       |
| `go_deadlock_002` | Deadlock from inconsistent mutex ordering | medium     |
| `go_chan_003`      | Unbuffered channel blocks forever         | easy       |
| `go_retry_004`    | Retry loop off-by-one error               | medium     |
| `go_grpc_005`     | Missing error handling in gRPC call       | easy       |

### Python (5 tests)

| ID                | Title                                 | Difficulty |
| ----------------- | ------------------------------------- | ---------- |
| `py_race_001`     | Race condition on shared list         | easy       |
| `py_deadlock_002` | Deadlock with non-reentrant lock      | medium     |
| `py_retry_003`    | Broken exponential backoff            | medium     |
| `py_socket_004`   | Missing error handling in socket code | easy       |
| `py_async_005`    | Asyncio task swallows cancellation    | hard       |

### Theory (2 tests)

| ID               | Title                     | Difficulty |
| ---------------- | ------------------------- | ---------- |
| `theory_cap_001` | CAP Theorem trade-offs    | medium     |
| `theory_bft_002` | Byzantine Fault Tolerance | hard       |

### Adding new tests

Create a new `.yaml` file anywhere under `benchmarks/`. It is auto-discovered — no code changes needed.

```yaml
id: unique_test_id        # must be unique across all tests
title: "Short description"
language: go               # go | python | theory (or any string)
difficulty: easy           # easy | medium | hard

prompt: |
  The prompt sent to the LLM. Describe what you want it to analyze.

code: |                    # optional — omit entirely for theory questions
  func main() {
      // buggy code here
  }

expected_issues:           # ground truth for judge scoring
  - "Description of bug 1"
  - "Description of bug 2"

notes: |                   # optional, not sent to the LLM
  Reviewer notes.
```

You can also create, edit, and delete tests directly from the web UI at `/tests`.

## Results Format

Results are stored as JSON files in `results/<model_name>/run_NNN/`.

### Per-test result (`<test_id>.json`)

```json
{
  "test_id": "go_race_001",
  "model": "llama3:8b",
  "prompt_sent": "[SYSTEM] ... [USER] ...",
  "response": "The raw LLM output...",
  "prompt_tokens": 150,
  "completion_tokens": 320,
  "total_tokens": 470,
  "elapsed_seconds": 4.23,
  "tokens_per_second": 75.7,
  "timestamp": "2025-03-26T10:30:00+00:00",
  "error": null
}
```

### Judge result (`<test_id>.judge.json`)

```json
{
  "test_id": "go_race_001",
  "judge_model": "gpt-5.2-chat-latest",
  "score": 15,
  "explanation": "The LLM correctly identified...",
  "issues_found": ["Race condition on counter"],
  "issues_expected": ["Unsynchronized access to shared counter"],
  "issues_matched": ["Unsynchronized access to shared counter"],
  "issues_missed": [],
  "timestamp": "2025-03-26T10:35:00+00:00",
  "judge_prompt_tokens": 1200,
  "judge_completion_tokens": 180,
  "judge_elapsed_seconds": 2.1,
  "error": null
}
```

### Run metadata (`metadata.json`)

```json
{
  "run_id": "run_001",
  "model": "llama3:8b",
  "api_url": "http://localhost:11434/v1",
  "timestamp": "2025-03-26T10:30:00+00:00",
  "temperature": 0.1,
  "max_tokens": 2048,
  "total_tests": 12,
  "total_elapsed_seconds": 58.4,
  "avg_tokens_per_second": 72.3,
  "test_ids": ["go_race_001", "..."],
  "provider": "ollama",
  "system_prompt": "You are a senior software engineer...",
  "think": false
}
```

## Architecture

```
src/
├── __init__.py
├── __main__.py              # Entry point — starts FastAPI server
├── models.py                # Frozen dataclasses for all data types
├── exceptions.py            # Domain exceptions
├── metrics.py               # Token throughput calculation
├── core/
│   ├── llm_client.py        # OpenAI SDK + Ollama native streaming client
│   ├── llm_protocol.py      # LLMClientProtocol for DI
│   ├── runner.py             # Benchmark execution with progress callbacks
│   ├── judge.py              # LLM judge scoring (1–20 rubric)
│   ├── loader.py             # YAML test case discovery and CRUD
│   ├── results.py            # JSON persistence for results/metadata/judge
│   ├── ollama_manager.py     # Async Ollama REST API (list/pull/delete)
│   └── leaderboard.py        # Cross-run score aggregation
├── web/
│   ├── app.py                # FastAPI app factory
│   ├── dependencies.py       # DI providers (Depends)
│   ├── task_manager.py       # Background task + SSE queue management
│   └── routes/
│       ├── dashboard.py      # GET /
│       ├── runs.py           # Run execution, detail, progress SSE
│       ├── tests.py          # Test CRUD
│       ├── ollama.py         # Ollama model management
│       ├── judge.py          # Judge trigger + SSE
│       ├── leaderboard.py    # Sortable leaderboard
│       ├── export.py         # CSV/Markdown download
│       └── compare.py        # Side-by-side comparison
├── templates/                # Jinja2 + HTMX + Tailwind templates
│   ├── base.html
│   ├── dashboard.html
│   ├── leaderboard.html
│   ├── run_detail.html
│   ├── test_detail.html
│   ├── compare.html
│   ├── runs/
│   ├── tests/
│   ├── ollama/
│   └── partials/
benchmarks/                       # YAML benchmark cases (auto-discovered)
├── go/
├── python/
└── theory/
tests/                            # Pytest test files

```

## Docker

```bash
# Build and run
docker compose build
docker compose up

# Or manually
docker build -t llm-bug-bench .
docker run --rm --network host -v $(pwd)/results:/app/results -v $(pwd)/benchmarks:/app/benchmarks llm-bug-bench
```

The container starts the web server on port 8080 by default.

## Development

```bash
# Install dependencies
poetry install

# Run formatters and linters
make precommit

# Start with debug logging
python -m src --debug
```

### Dependencies

| Package          | Purpose                              |
| ---------------- | ------------------------------------ |
| `fastapi`        | Web framework                        |
| `uvicorn`        | ASGI server                          |
| `jinja2`         | Template engine                      |
| `openai`         | LLM API client (all providers)       |
| `httpx`          | Async HTTP for Ollama management API |
| `pyyaml`         | YAML test case parsing               |
| `python-dotenv`  | `.env` file loading                  |
| `python-multipart`| Form data handling                  |
