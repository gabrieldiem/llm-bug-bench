PORT ?= 8080
RESULTS_DIR ?= ./results
TESTS_DIR ?= ./tests

.PHONY: up down clean prod build test results precommit help

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  %-15s %s\n", $$1, $$2}'

up: ## Start dev environment (hot-reload, source mounted)
	docker compose -f docker-compose-dev.yaml up --build

down: ## Stop all containers
	docker compose down 2>/dev/null; docker compose -f docker-compose-dev.yaml down 2>/dev/null; true

clean: ## Stop containers and delete results
	docker compose -f docker-compose-dev.yaml down -v 2>/dev/null; true
	rm -rf $(RESULTS_DIR)

prod: ## Start production environment
	docker compose up --build

build: ## Build production Docker image
	docker compose build

test: ## Run tests with coverage via Docker
	docker build -f Dockerfile.run_test -t llm-bug-bench-test . && \
	docker run --rm -v ./reports:/app/reports llm-bug-bench-test; \
	ret=$$?; if [ $$ret -eq 5 ]; then echo "No tests collected (exit 5) — OK"; exit 0; fi; exit $$ret

results: ## Print summary of all saved runs
	@find $(RESULTS_DIR) -name "metadata.json" 2>/dev/null \
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

precommit: ## Run formatters and linters
	pre-commit run --all-files
