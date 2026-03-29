PORT ?= 8080
RESULTS_DIR ?= ./results
TESTS_DIR ?= ./tests

.PHONY: serve build clean results help precommit

help:
	@echo "Usage:"
	@echo "  make serve                  Start the web UI (default)"
	@echo "  make build                  Build the Docker image"
	@echo "  make clean                  Remove all results"
	@echo "  make results                List all result runs"
	@echo "  make precommit              Run formatters and linters"
	@echo ""
	@echo "Variables (override with make serve VAR=value):"
	@echo "  PORT=$(PORT)"
	@echo "  RESULTS_DIR=$(RESULTS_DIR)"
	@echo "  TESTS_DIR=$(TESTS_DIR)"

serve:
	python -m src --port $(PORT) --results-dir $(RESULTS_DIR) --tests-dir $(TESTS_DIR)

build:
	docker compose build

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
