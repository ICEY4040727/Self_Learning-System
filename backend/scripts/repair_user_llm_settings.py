"""Data-repair entry point for User LLM settings.

Prefer the guarded DBA runner (pre/post audit + staging gate):

    python -m backend.scripts.dba_user_llm_runner repair \\
        --username testuser --staging-validated --validation-ref CHANGE-123

Dry-run:

    python -m backend.scripts.dba_user_llm_runner repair \\
        --username testuser --staging-validated --dry-run
"""
from __future__ import annotations

import argparse
import logging
import sys

from backend.scripts.dba_user_llm_runner import DBAUserLLMValidationError, main as runner_main

logger = logging.getLogger("repair_user_llm_settings")


def main(argv: list[str] | None = None) -> int:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--username", help="Target username")
    parser.add_argument("--user-id", type=int, help="Target user id")
    parser.add_argument(
        "--staging-validated",
        action="store_true",
        help="Required: confirm staging/pre-release validation",
    )
    parser.add_argument("--validation-ref", help="Ticket/change id from staging validation")
    parser.add_argument("--dry-run", action="store_true", help="Pre-audit only")
    args = parser.parse_args(argv)

    if not args.staging_validated:
        parser.error("--staging-validated is required (use dba_user_llm_runner flow)")

    forwarded = ["repair"]
    if args.username:
        forwarded.extend(["--username", args.username])
    if args.user_id is not None:
        forwarded.extend(["--user-id", str(args.user_id)])
    forwarded.append("--staging-validated")
    if args.validation_ref:
        forwarded.extend(["--validation-ref", args.validation_ref])
    if args.dry_run:
        forwarded.append("--dry-run")

    try:
        return runner_main(forwarded)
    except DBAUserLLMValidationError as exc:
        logger.error("%s", exc)
        return 1


if __name__ == "__main__":
    sys.exit(main())
