import argparse
import os

from dotenv import load_dotenv


def main() -> None:
    load_dotenv()

    parser = argparse.ArgumentParser(
        prog="bizwatcher",
        description="Byzantine Watcher — LLM bug-detection benchmark suite",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=int(os.environ.get("PORT", "8080")),
        help="Port to listen on",
    )
    parser.add_argument(
        "--results-dir",
        default=os.environ.get("RESULTS_DIR", "./results"),
        help="Directory with run results",
    )
    parser.add_argument(
        "--tests-dir",
        default=os.environ.get("TESTS_DIR", "./tests"),
        help="Directory with YAML test cases",
    )

    args = parser.parse_args()

    import uvicorn

    from .web.app import create_app

    app = create_app(
        results_dir=args.results_dir,
        tests_dir=args.tests_dir,
    )
    uvicorn.run(app, host="0.0.0.0", port=args.port)


if __name__ == "__main__":
    main()
