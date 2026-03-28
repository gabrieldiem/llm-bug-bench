MODEL ?= llama3:8b
API_URL ?= http://localhost:11434/v1
TAGS ?=
TEMPERATURE ?= 0.1
MAX_TOKENS ?= 2048
PORT ?= 8080
RUN_DIR ?=
JUDGE_MODEL ?= gpt-5.2-chat-latest
TESTS_DIR ?= ./tests

# Build flags for docker compose run
_RUN_ARGS = run --api-url $(API_URL) --model $(MODEL) --temperature $(TEMPERATURE) --max-tokens $(MAX_TOKENS)
ifneq ($(TAGS),)
  _RUN_ARGS += --tags $(TAGS)
endif

.PHONY: build run run-local judge serve clean results help

help:
	@echo "Usage:"
	@echo "  make build                  Build the Docker image"
	@echo "  make run                    Run the full test suite (Docker)"
	@echo "  make run-local              Run without Docker (requires pip install)"
	@echo "  make judge                  Score a run with an LLM judge (RUN_DIR=required)"
	@echo "  make serve                  Start the web UI (PORT=8080)"
	@echo "  make clean                  Remove all results"
	@echo "  make results                List all result runs"
	@echo ""
	@echo "Variables (override with make run VAR=value):"
	@echo "  MODEL=$(MODEL)"
	@echo "  API_URL=$(API_URL)"
	@echo "  TAGS=$(TAGS)          (comma-separated, e.g. TAGS=deadlock,retry)"
	@echo "  TEMPERATURE=$(TEMPERATURE)"
	@echo "  MAX_TOKENS=$(MAX_TOKENS)"
	@echo "  PORT=$(PORT)"
	@echo "  RUN_DIR=$(RUN_DIR)          (required for judge)"
	@echo "  JUDGE_MODEL=$(JUDGE_MODEL)"
	@echo "  TESTS_DIR=$(TESTS_DIR)"

build:
	docker compose build

run: build
	docker compose run --rm bizwatcher $(_RUN_ARGS)

run-local:
	pip install -q -r requirements.txt
	python -m bizwatcher $(_RUN_ARGS)

judge:
	@test -n "$(RUN_DIR)" || (echo "Error: RUN_DIR is required. Usage: make judge RUN_DIR=results/<model>/run_001"; exit 1)
	python -m bizwatcher judge --run-dir $(RUN_DIR) --tests-dir $(TESTS_DIR) --judge-model $(JUDGE_MODEL)

serve:
	python -m bizwatcher serve --port $(PORT)

clean:
	rm -rf results/

results:
	@find results -name "metadata.json" 2>/dev/null \
	  | sort \
	  | xargs -I{} sh -c 'echo "--- {} ---"; cat {}' \
	  | python3 -c "\
import sys, json, re; \
data = sys.stdin.read(); \
blocks = re.split(r'--- (.*?) ---\n', data)[1:]; \
pairs = zip(blocks[::2], blocks[1::2]); \
[print(f\"{path}\n  model={m['model']}  run={m['run_id']}  tests={m['total_tests']}  elapsed={m['total_elapsed_seconds']}s  avg_tps={m['avg_tokens_per_second']}\n\") \
  for path, raw in pairs \
  for m in [json.loads(raw)]]" 2>/dev/null || echo "No results found."

precommit:
	pre-commit run --all-files
