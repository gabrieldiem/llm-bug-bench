MODEL ?= llama3:8b
API_URL ?= http://localhost:11434/v1
TAGS ?=
TEMPERATURE ?= 0.1
MAX_TOKENS ?= 2048

# Build flags for docker compose run
_ARGS = --api-url $(API_URL) --model $(MODEL) --temperature $(TEMPERATURE) --max-tokens $(MAX_TOKENS)
ifneq ($(TAGS),)
  _ARGS += --tags $(TAGS)
endif

.PHONY: build run run-local clean results help

help:
	@echo "Usage:"
	@echo "  make build                  Build the Docker image"
	@echo "  make run                    Run the full test suite (Docker)"
	@echo "  make run-local              Run without Docker (requires pip install)"
	@echo "  make clean                  Remove all results"
	@echo "  make results                List all result runs"
	@echo ""
	@echo "Variables (override with make run VAR=value):"
	@echo "  MODEL=$(MODEL)"
	@echo "  API_URL=$(API_URL)"
	@echo "  TAGS=$(TAGS)          (comma-separated, e.g. TAGS=deadlock,retry)"
	@echo "  TEMPERATURE=$(TEMPERATURE)"
	@echo "  MAX_TOKENS=$(MAX_TOKENS)"

build:
	docker compose build

run: build
	docker compose run --rm bizwatcher $(_ARGS)

run-local:
	pip install -q -r requirements.txt
	python -m bizwatcher $(_ARGS)

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
