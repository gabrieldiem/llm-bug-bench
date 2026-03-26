# bizantine-watcher

A Dockerized benchmark suite that tests small/local LLMs on their ability to detect bugs in code. Focused on concurrency issues, error handling, and distributed systems patterns in Go and Python, plus theoretical questions.

The tool sends buggy code snippets to an OpenAI-compatible API (Ollama, LM Studio, vLLM, llama.cpp, etc.), records the raw LLM output for manual review, and measures response speed (tokens/sec).

## Quick Start

```bash
# Build and run against a local Ollama model
make run MODEL=llama3:8b

# Run with a different model or API
make run MODEL=qwen2:7b API_URL=http://localhost:11434/v1

# Run only specific test categories
make run MODEL=llama3:8b TAGS=deadlock,retry

# Show all previous results
make results
```

Results are saved to `results/<model_name>/run_001/`.

## Makefile Reference

| Target           | Description                                    |
| ---------------- | ---------------------------------------------- |
| `make build`     | Build the Docker image                         |
| `make run`       | Build and run the full suite (Docker)          |
| `make run-local` | Run without Docker (pip-installs dependencies) |
| `make results`   | Print a summary of all saved runs              |
| `make clean`     | Delete all results                             |

Variables (all optional, override on the command line):

| Variable      | Default                     | Description                           |
| ------------- | --------------------------- | ------------------------------------- |
| `MODEL`       | `llama3:8b`                 | Model name passed to the API          |
| `API_URL`     | `http://localhost:11434/v1` | Base URL of the OpenAI-compatible API |
| `TAGS`        | —                           | Comma-separated tag filter            |
| `TEMPERATURE` | `0.1`                       | Sampling temperature                  |
| `MAX_TOKENS`  | `2048`                      | Max response tokens                   |

## Requirements

- Docker and Docker Compose
- An OpenAI-compatible LLM server running locally (e.g., [Ollama](https://ollama.com))

## CLI Reference

```
python -m bizwatcher --api-url <URL> --model <MODEL> [OPTIONS]
```

| Argument          | Required | Default     | Description                                                               |
| ----------------- | -------- | ----------- | ------------------------------------------------------------------------- |
| `--api-url`       | Yes      | —           | Base URL of the OpenAI-compatible API (e.g., `http://localhost:11434/v1`) |
| `--model`         | Yes      | —           | Model name passed to the API and used for organizing results              |
| `--tests-dir`     | No       | `./tests`   | Directory containing YAML test case files                                 |
| `--results-dir`   | No       | `./results` | Directory where results are written                                       |
| `--temperature`   | No       | `0.1`       | Sampling temperature (lower = more deterministic)                         |
| `--max-tokens`    | No       | `2048`      | Maximum tokens in the LLM response                                        |
| `--tags`          | No       | —           | Comma-separated tag filter; only runs tests matching at least one tag     |
| `--system-prompt` | No       | Built-in    | Override the default system prompt                                        |

## Running with Docker

### Using docker compose (recommended)

Edit `docker-compose.yml` to set your default model and API URL:

```yaml
services:
  bizwatcher:
    build: .
    network_mode: host
    volumes:
      - ./results:/app/results
      - ./tests:/app/tests
    command: >
      --api-url http://localhost:11434/v1
      --model llama3:8b
```

Then run:

```bash
docker compose build
docker compose run bizwatcher
```

Override the model at runtime:

```bash
docker compose run bizwatcher --api-url http://localhost:11434/v1 --model qwen2:7b
```

### Using docker directly

```bash
docker build -t bizwatcher .

docker run --rm --network host \
  -v $(pwd)/results:/app/results \
  -v $(pwd)/tests:/app/tests \
  bizwatcher \
  --api-url http://localhost:11434/v1 \
  --model llama3:8b
```

### Running without Docker

```bash
pip install -r requirements.txt

python -m bizwatcher \
  --api-url http://localhost:11434/v1 \
  --model llama3:8b
```

## Test Suite

The suite ships with 12 test cases across three categories:

### Go (5 tests)

| ID                | Title                                     | Tags                                      | Difficulty |
| ----------------- | ----------------------------------------- | ----------------------------------------- | ---------- |
| `go_race_001`     | Race condition in concurrent counter      | race-condition, goroutine, mutex          | easy       |
| `go_deadlock_002` | Deadlock from inconsistent mutex ordering | deadlock, mutex, goroutine                | medium     |
| `go_chan_003`     | Unbuffered channel blocks forever         | channel, goroutine, deadlock              | easy       |
| `go_retry_004`    | Retry loop off-by-one error               | retry, off-by-one, distributed-systems    | medium     |
| `go_grpc_005`     | Missing error handling in gRPC call       | error-handling, grpc, distributed-systems | easy       |

### Python (5 tests)

| ID                | Title                                 | Tags                                 | Difficulty |
| ----------------- | ------------------------------------- | ------------------------------------ | ---------- |
| `py_race_001`     | Race condition on shared list         | race-condition, threading            | easy       |
| `py_deadlock_002` | Deadlock with non-reentrant lock      | deadlock, threading, lock            | medium     |
| `py_retry_003`    | Broken exponential backoff            | retry, backoff, distributed-systems  | medium     |
| `py_socket_004`   | Missing error handling in socket code | error-handling, socket, networking   | easy       |
| `py_async_005`    | Asyncio task swallows cancellation    | asyncio, cancellation, resource-leak | hard       |

### Theory (2 tests)

| ID               | Title                     | Tags                                            | Difficulty |
| ---------------- | ------------------------- | ----------------------------------------------- | ---------- |
| `theory_cap_001` | CAP Theorem trade-offs    | cap-theorem, distributed-systems                | medium     |
| `theory_bft_002` | Byzantine Fault Tolerance | byzantine, fault-tolerance, distributed-systems | hard       |

### Filtering by tags

Run only specific categories:

```bash
# Only deadlock-related tests
docker compose run bizwatcher --api-url http://localhost:11434/v1 --model llama3:8b --tags deadlock

# Only distributed systems topics
docker compose run bizwatcher --api-url http://localhost:11434/v1 --model llama3:8b --tags distributed-systems

# Multiple tags (runs tests matching ANY of the tags)
docker compose run bizwatcher --api-url http://localhost:11434/v1 --model llama3:8b --tags "race-condition,deadlock"
```

## Results

Results are organized by model name and auto-incrementing run ID:

```
results/
  llama3_8b/
    run_001/
      metadata.json
      go_race_001.json
      go_deadlock_002.json
      ...
    run_002/
      ...
  qwen2_7b/
    run_001/
      ...
```

Running the same model multiple times auto-increments the run ID (`run_001`, `run_002`, ...).

### Per-test result file

Each `<test_id>.json` contains:

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

### Run metadata file

Each `metadata.json` contains aggregate info:

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
  "test_ids": ["go_race_001", "go_deadlock_002", "..."]
}
```

## Adding New Tests

Create a new `.yaml` file anywhere under `tests/`. It is auto-discovered on the next run — no code changes needed.

### Test case schema

```yaml
id: unique_test_id # must be unique across all tests
title: "Short description"
language: go # go | python | theory (or any string)
tags: [tag1, tag2] # used for --tags filtering
difficulty: easy # easy | medium | hard (informational only)

prompt: |
  The prompt sent to the LLM. Describe what you want it to analyze.

code: | # omit entirely for theory questions
  // The buggy code goes here
  func main() {
      // ...
  }

expected_issues: # for your own reference when reviewing results
  - "Description of bug 1"
  - "Description of bug 2"

notes: | # optional, not sent to the LLM
  Any reviewer notes.
```

- `id`, `title`, `language`, `tags`, `difficulty`, and `prompt` are required.
- `code` is optional (omit for theory questions). When present, it is appended to the prompt in a fenced code block.
- `expected_issues` and `notes` are never sent to the LLM — they exist only to help you review results.

### Example: adding a Rust test

```bash
mkdir -p tests/rust
```

Create `tests/rust/001_use_after_move.yaml`:

```yaml
id: rust_move_001
title: "Use after move"
language: rust
tags: [ownership, move-semantics]
difficulty: easy

prompt: |
  Identify the compilation error in this Rust code and explain why it occurs.

code: |
  fn main() {
      let s = String::from("hello");
      let t = s;
      println!("{}", s);
  }

expected_issues:
  - "s is used after being moved to t"
```

Run the suite again and the new test is automatically picked up.

## Speed Metrics

The tool measures tokens/sec using the `usage` field from the API response:

```
tokens/sec = completion_tokens / elapsed_seconds
```

Ollama, vLLM, LM Studio, and llama.cpp all return token counts in the standard OpenAI response format. If a provider does not return usage data, the metric is skipped and a warning is printed.

## Project Structure

```
bizantine-watcher/
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
├── bizwatcher/
│   ├── __init__.py
│   ├── __main__.py       # CLI entry point (argparse)
│   ├── runner.py          # Core test runner loop
│   ├── client.py          # OpenAI API client wrapper
│   ├── models.py          # Dataclasses: TestCase, TestResult, RunMetadata
│   ├── loader.py          # YAML test discovery and deserialization
│   ├── results.py         # Results directory management, JSON output
│   └── metrics.py         # Tokens/sec calculation
├── tests/                 # YAML test cases (auto-discovered recursively)
│   ├── go/
│   ├── python/
│   └── theory/
└── results/               # Output (gitignored)
```
