"""CLI entry point — starts the FastAPI web server."""

import argparse
import os

from dotenv import load_dotenv


def _build_log_config(debug: bool) -> dict:
    """Build a dictConfig-compatible log config to pass to uvicorn."""
    level = "DEBUG" if debug else "INFO"
    return {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "default": {
                "format": "%(asctime)s %(levelname)-8s %(name)s — %(message)s",
                "datefmt": "%Y-%m-%d %H:%M:%S",
            },
        },
        "handlers": {
            "default": {
                "class": "logging.StreamHandler",
                "formatter": "default",
                "stream": "ext://sys.stderr",
            },
        },
        "root": {
            "level": level,
            "handlers": ["default"],
        },
        "loggers": {
            "uvicorn.access": {"level": "WARNING"},
            "httpx": {"level": "WARNING"},
            "httpcore": {"level": "WARNING"},
            "openai": {"level": "WARNING"},
        },
    }


def main() -> None:
    """Parse CLI args and start the uvicorn server."""
    load_dotenv()

    parser = argparse.ArgumentParser(
        prog="llm-bug-bench",
        description="LLM Bug Detection Benchmark Suite",
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
        "--benchmarks-dir",
        default=os.environ.get("BENCHMARKS_DIR", "./benchmarks"),
        help="Directory with YAML test cases",
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        default=False,
        help="Enable debug logging",
    )
    parser.add_argument(
        "--reload",
        action="store_true",
        default=False,
        help="Enable uvicorn auto-reload (for development)",
    )

    args = parser.parse_args()
    log_config = _build_log_config(args.debug)

    import uvicorn

    if args.reload:
        uvicorn.run(
            "src.web.app:create_app",
            factory=True,
            host="0.0.0.0",
            port=args.port,
            reload=True,
            reload_dirs=["src"],
            log_config=log_config,
        )
    else:
        from .web.app import create_app

        app = create_app(
            results_dir=args.results_dir,
            benchmarks_dir=args.benchmarks_dir,
        )
        uvicorn.run(app, host="0.0.0.0", port=args.port, log_config=log_config)


if __name__ == "__main__":
    main()
