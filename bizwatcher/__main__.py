import argparse

from .runner import run


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="bizwatcher",
        description="Benchmark LLMs on bug detection tasks",
    )
    parser.add_argument("--api-url", required=True, help="Base URL of OpenAI-compatible API")
    parser.add_argument("--model", required=True, help="Model name for API calls and logging")
    parser.add_argument("--tests-dir", default="./tests", help="Directory with YAML test cases")
    parser.add_argument("--results-dir", default="./results", help="Directory for output")
    parser.add_argument("--temperature", type=float, default=0.1, help="Sampling temperature")
    parser.add_argument("--max-tokens", type=int, default=2048, help="Max response tokens")
    parser.add_argument("--tags", type=lambda s: s.split(","), default=None, help="Comma-separated tag filter")
    parser.add_argument("--system-prompt", default=None, help="Override default system prompt")

    args = parser.parse_args()
    run(args)


if __name__ == "__main__":
    main()
