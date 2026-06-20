"""In-container scheduler for nightly User LLM consistency patrol."""
from __future__ import annotations

import argparse
import logging
import os
import shlex
import subprocess
import sys
import time
from datetime import datetime, timedelta

logger = logging.getLogger("user_llm_patrol_scheduler")

DEFAULT_PATROL_ARGS = "--sql --repair --fail-on-issues"
DEFAULT_RUN_AT = "03:00"


def _parse_run_at(value: str) -> tuple[int, int]:
    hour_text, minute_text = value.split(":", 1)
    hour = int(hour_text)
    minute = int(minute_text)
    if not (0 <= hour <= 23 and 0 <= minute <= 59):
        raise ValueError(f"Invalid run-at time: {value!r}")
    return hour, minute


def _next_run_at(hour: int, minute: int, *, now: datetime | None = None) -> datetime:
    current = now or datetime.now()
    target = current.replace(hour=hour, minute=minute, second=0, microsecond=0)
    if target <= current:
        target += timedelta(days=1)
    return target


def _run_patrol(patrol_args: list[str]) -> int:
    command = [sys.executable, "-m", "backend.scripts.audit_user_llm_consistency_job", *patrol_args]
    logger.info("Starting patrol: %s", " ".join(command))
    completed = subprocess.run(command, check=False)
    if completed.returncode != 0:
        logger.error("Patrol exited with code %s", completed.returncode)
    else:
        logger.info("Patrol completed successfully")
    return completed.returncode


def main(argv: list[str] | None = None) -> int:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--run-at",
        default=os.getenv("USER_LLM_PATROL_RUN_AT", DEFAULT_RUN_AT),
        help="Daily local time HH:MM (default: 03:00 or USER_LLM_PATROL_RUN_AT)",
    )
    parser.add_argument(
        "--patrol-args",
        default=os.getenv("USER_LLM_PATROL_ARGS", DEFAULT_PATROL_ARGS),
        help="Arguments forwarded to audit_user_llm_consistency_job",
    )
    parser.add_argument(
        "--run-on-start",
        action="store_true",
        default=os.getenv("USER_LLM_PATROL_RUN_ON_START", "").lower() in {"1", "true", "yes"},
        help="Run one patrol immediately before entering the schedule loop",
    )
    parser.add_argument(
        "--once",
        action="store_true",
        help="Run patrol once and exit (for CI/manual smoke)",
    )
    args = parser.parse_args(argv)

    hour, minute = _parse_run_at(args.run_at)
    patrol_args = shlex.split(args.patrol_args)

    if args.once:
        return _run_patrol(patrol_args)

    if args.run_on_start:
        _run_patrol(patrol_args)

    logger.info("User LLM patrol scheduler active; next run at %02d:%02d daily", hour, minute)
    while True:
        target = _next_run_at(hour, minute)
        sleep_seconds = max(1, int((target - datetime.now()).total_seconds()))
        logger.info("Sleeping %s seconds until %s", sleep_seconds, target.isoformat(timespec="seconds"))
        time.sleep(sleep_seconds)
        _run_patrol(patrol_args)


if __name__ == "__main__":
    sys.exit(main())
