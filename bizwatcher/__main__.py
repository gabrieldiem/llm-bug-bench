import argparse

from dotenv import load_dotenv


def _add_run_subparser(subparsers: argparse._SubParsersAction) -> None:
    p = subparsers.add_parser("run", help="Run the benchmark against an LLM")
    p.add_argument("--api-url", required=True, help="Base URL of OpenAI-compatible API")
    p.add_argument(
        "--model", required=True, help="Model name for API calls and logging"
    )
    p.add_argument(
        "--tests-dir", default="./tests", help="Directory with YAML test cases"
    )
    p.add_argument("--results-dir", default="./results", help="Directory for output")
    p.add_argument(
        "--temperature", type=float, default=0.1, help="Sampling temperature"
    )
    p.add_argument("--max-tokens", type=int, default=2048, help="Max response tokens")
    p.add_argument(
        "--tags",
        type=lambda s: s.split(","),
        default=None,
        help="Comma-separated tag filter",
    )
    p.add_argument(
        "--system-prompt", default=None, help="Override default system prompt"
    )
    p.add_argument(
        "--think",
        action="store_true",
        default=False,
        help="Enable thinking/reasoning mode (disabled by default)",
    )
    p.add_argument(
        "--debug",
        action="store_true",
        default=False,
        help="Print raw stream chunks to stderr for debugging",
    )


def _add_judge_subparser(subparsers: argparse._SubParsersAction) -> None:
    p = subparsers.add_parser("judge", help="Score saved results using an LLM judge")
    p.add_argument("--run-dir", required=True, help="Path to a run_NNN directory")
    p.add_argument(
        "--tests-dir", default="./tests", help="Directory with YAML test cases"
    )
    p.add_argument(
        "--judge-model",
        default="gpt-5.2-chat-latest",
        help="OpenAI model to use as judge",
    )


def _add_serve_subparser(subparsers: argparse._SubParsersAction) -> None:
    p = subparsers.add_parser("serve", help="Start the web UI")
    p.add_argument("--port", type=int, default=8080, help="Port to listen on")
    p.add_argument(
        "--results-dir", default="./results", help="Directory with run results"
    )


def _dispatch(args: argparse.Namespace) -> None:
    if args.command == "run":
        from .runner import run

        run(args)
    elif args.command == "judge":
        from .judge import judge

        judge(args)
    elif args.command == "serve":
        from .web import serve

        serve(args)


def main() -> None:
    load_dotenv()
    parser = argparse.ArgumentParser(
        prog="bizwatcher",
        description="Benchmark LLMs on bug detection tasks",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)
    _add_run_subparser(subparsers)
    _add_judge_subparser(subparsers)
    _add_serve_subparser(subparsers)

    args = parser.parse_args()
    _dispatch(args)


if __name__ == "__main__":
    main()
