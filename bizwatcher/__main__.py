"""CLI entry point — starts the FastAPI web server."""

import argparse
import logging
import os

from dotenv import load_dotenv


def _configure_logging(debug: bool) -> None:
    """Set up root logger and suppress noisy third-party loggers."""
    level = logging.DEBUG if debug else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s %(levelname)-8s %(name)s — %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    for noisy in ("uvicorn.access", "httpx", "httpcore", "openai"):
        logging.getLogger(noisy).setLevel(logging.WARNING)


def main() -> None:
    """Parse CLI args and start the uvicorn server."""
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
    parser.add_argument(
        "--debug",
        action="store_true",
        default=False,
        help="Enable debug logging",
    )

    args = parser.parse_args()
    _configure_logging(args.debug)

    import uvicorn

    from .web.app import create_app

    app = create_app(
        results_dir=args.results_dir,
        tests_dir=args.tests_dir,
    )
    uvicorn.run(app, host="0.0.0.0", port=args.port)


if __name__ == "__main__":
    main()
