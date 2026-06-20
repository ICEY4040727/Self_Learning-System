"""Scheduled User LLM JSON/legacy consistency patrol entry point.

Examples:
    python -m backend.scripts.audit_user_llm_consistency_job --sql --fail-on-issues
    python -m backend.scripts.audit_user_llm_consistency_job --sql --repair --fail-on-issues
    python -m backend.scripts.audit_user_llm_consistency_job --sql --dry-run --fail-on-issues
"""
from __future__ import annotations

import argparse
import logging
import sys

from backend.db.database import SessionLocal
from backend.services.user_llm_alerts import notify_patrol_exception, notify_patrol_result
from backend.services.user_llm_db_audit import (
    count_legacy_backfill_candidates,
    format_audit_report,
)
from backend.services.user_llm_repair import patrol_exit_code, patrol_user_llm_consistency
from backend.services.user_llm_telemetry import log_patrol_metrics

logger = logging.getLogger("audit_user_llm_consistency_job")


def main(argv: list[str] | None = None) -> int:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--sql",
        action="store_true",
        help="Use SQL full-table scan on PostgreSQL (ORM fallback on SQLite)",
    )
    parser.add_argument(
        "--repair",
        action="store_true",
        help="Repair inconsistent rows via the write gateway",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Scan only; alias for scan without --repair",
    )
    parser.add_argument(
        "--fail-on-issues",
        action="store_true",
        help="Exit non-zero when inconsistencies remain after the run",
    )
    args = parser.parse_args(argv)

    apply_repair = args.repair and not args.dry_run
    session = SessionLocal()
    try:
        legacy_backfill_candidates = count_legacy_backfill_candidates(session)
        result = patrol_user_llm_consistency(
            session,
            use_sql=args.sql,
            apply_repair=apply_repair,
        )
        exit_code = patrol_exit_code(result, fail_on_issues=args.fail_on_issues)
        log_patrol_metrics(
            pre_issue_count=len(result.pre_issues),
            post_issue_count=len(result.post_issues),
            legacy_backfill_candidate_count=legacy_backfill_candidates,
            repaired_user_count=result.repaired_user_count,
            repair_error_count=len(result.repair_errors),
            applied_repair=apply_repair,
            exit_code=exit_code,
        )

        if result.pre_issues or result.post_issues:
            logger.warning(
                "Patrol report:\n%s",
                format_audit_report(result.post_issues or result.pre_issues),
            )
        else:
            logger.info("Patrol report: OK")

        notify_patrol_result(
            result,
            exit_code=exit_code,
            dry_run=not apply_repair,
            applied_repair=apply_repair,
        )
        return exit_code
    except Exception as exc:
        logger.exception("Patrol job failed")
        notify_patrol_exception(error=str(exc))
        return 1
    finally:
        session.close()


if __name__ == "__main__":
    sys.exit(main())
