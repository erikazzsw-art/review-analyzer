from __future__ import annotations

import argparse
import os

from .queue import get_queue, get_redis_connection


def run_worker(burst: bool = False) -> None:
    try:
        from rq import Worker
    except ImportError as exc:  # pragma: no cover - runtime dependency guard
        raise RuntimeError(
            "RQ support is not installed. Install `redis` and `rq` to run workers."
        ) from exc

    queue = get_queue()
    connection = get_redis_connection()
    worker_name = os.getenv("RQ_WORKER_NAME", "clueai-worker")
    worker = Worker([queue], connection=connection, name=worker_name)
    worker.work(burst=burst)


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the ClueAI RQ worker.")
    parser.add_argument("--burst", action="store_true", help="Process queued jobs once and exit.")
    args = parser.parse_args()
    run_worker(burst=bool(args.burst))


if __name__ == "__main__":
    main()

