# CLAUDE.md

## Project Overview

`bizantine-watcher` — Benchmark suite evaluating local LLMs' bug-detection ability. Sends buggy code to OpenAI-compatible APIs (Ollama, vLLM, LM Studio, llama.cpp), measures detection accuracy and speed.

## Commands

```bash
# Docker (recommended)
make run MODEL=llama3:8b API_URL=http://localhost:11434/v1
make run MODEL=llama3:8b TAGS=deadlock,retry

# Local
poetry install
make run-local MODEL=llama3:8b
python -m bizwatcher --api-url http://localhost:11434/v1 --model llama3:8b

# Utils
make build      # build image
make results    # print summary
make clean      # delete results
```

**CLI args:** `--api-url`, `--model`, `--tests-dir`, `--results-dir`, `--temperature` (0.1), `--max-tokens` (2048), `--tags`, `--system-prompt`

## Architecture

`__main__.py` → `runner.py` → `client.py` / `loader.py` / `results.py` / `metrics.py`

| Module | Purpose |
|--------|---------|
| `runner.py` | Core loop: load tests → create versioned run dir → query LLM → save JSON |
| `client.py` | OpenAI SDK wrapper for any compatible endpoint |
| `loader.py` | Discovers `.yaml` tests recursively; tag filtering (OR logic) |
| `models.py` | Dataclasses: `TestCase`, `TestResult`, `RunMetadata` |
| `results.py` | Output dirs at `results/<model>/run_NNN/`; sanitizes names |
| `metrics.py` | Computes tokens/second |

## Test Cases

YAML files in `tests/`, auto-discovered. Fields: `id`, `title`, `language`, `tags`, `difficulty`, `prompt`, `code` (optional), `expected_issues`, `notes`.

12 tests: 5 Go, 5 Python, 2 theory (CAP, Byzantine faults).

## Dependencies

Python 3.13+, Poetry, `openai>=2.30.0`, `pyyaml>=6.0.3`, Docker + local LLM server.

---

## Collaboration Protocol

1. **Before coding**: Describe approach → wait for approval. Ask if requirements are ambiguous.
2. **>3 file changes**: Stop. Break into smaller tasks.
3. **After coding**: List what could break and which tests need adding.

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
- `concurrent.futures.ThreadPoolExecutor` for blocking I/O.
- Batch small operations; lazy evaluation for expensive computations.

## Anti-Patterns

- ❌ God objects, circular deps, global mutable state
- ❌ Mixing business logic with infrastructure
- ❌ Unbounded concurrent task creation
- ❌ Catching `Exception` without re-raise
- ❌ Not cleaning up resources in error paths
