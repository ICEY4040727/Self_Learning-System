"""Run high-risk User LLM DBA scripts with pre/post consistency checks.

Usage:
    python -m backend.scripts.dba_user_llm_runner audit
    python -m backend.scripts.dba_user_llm_runner repair --username testuser --staging-validated
"""
from __future__ import annotations

import argparse
import logging
import sys
from collections.abc import Callable
from dataclasses import dataclass

from sqlalchemy.orm import Session

from backend.db.database import SessionLocal
from backend.services.user_llm_db_audit import (
    UserLLMInconsistency,
    audit_user_llm_consistency,
    format_audit_report,
)
from backend.services.user_llm_db_guard import user_llm_repair_mode
from backend.services.user_llm_telemetry import log_audit_issues

logger = logging.getLogger("dba_user_llm_runner")


class DBAUserLLMValidationError(RuntimeError):
    """Pre/post audit failed for a DBA script."""


@dataclass(frozen=True)
class DBAUserLLMRunResult:
    pre_issues: list[UserLLMInconsistency]
    post_issues: list[UserLLMInconsistency]
    applied: bool


def run_dba_user_llm_script(
    session: Session,
    action: Callable[[Session], None],
    *,
    staging_validated: bool,
    validation_ref: str | None = None,
    fail_on_preexisting_issues: bool = False,
    apply: bool = True,
) -> DBAUserLLMRunResult:
    """Execute a DBA action with mandatory staging gate and post-audit."""
    if not staging_validated:
        raise DBAUserLLMValidationError(
            "High-risk User LLM DBA scripts require --staging-validated "
            "(must pass pre-release/staging checks first)."
        )

    pre_issues = audit_user_llm_consistency(session)
    if pre_issues:
        logger.warning("Pre-audit found issues:\n%s", format_audit_report(pre_issues))
        if fail_on_preexisting_issues:
            raise DBAUserLLMValidationError(
                "Pre-audit failed; refusing to run DBA script on inconsistent data."
            )

    if validation_ref:
        logger.info("Staging validation reference: %s", validation_ref)

    if apply:
        with user_llm_repair_mode(session):
            action(session)
            session.commit()
    else:
        session.rollback()

    post_issues = audit_user_llm_consistency(session)
    if apply:
        log_audit_issues(post_issues)
    if apply and post_issues:
        raise DBAUserLLMValidationError(
            "Post-audit failed; JSON/legacy mirror is inconsistent:\n"
            + format_audit_report(post_issues)
        )

    return DBAUserLLMRunResult(
        pre_issues=pre_issues,
        post_issues=post_issues,
        applied=apply,
    )


def _repair_action(session: Session, *, username: str | None, user_id: int | None) -> None:
    from backend.models.models import User
    from backend.services.user_llm_repair import repair_user_llm_from_effective_config

    query = session.query(User)
    if user_id is not None:
        query = query.filter(User.id == user_id)
    elif username:
        query = query.filter(User.username == username)
    else:
        raise ValueError("Provide --username or --user-id for repair")

    user = query.one()
    repair_user_llm_from_effective_config(session, user)


def _audit_only(session: Session) -> None:
    issues = audit_user_llm_consistency(session)
    print(format_audit_report(issues))
    if issues:
        raise DBAUserLLMValidationError(format_audit_report(issues))


def main(argv: list[str] | None = None) -> int:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    audit_parser = sub.add_parser("audit", help="Audit JSON vs legacy consistency")
    audit_parser.add_argument(
        "--fail-on-issues",
        action="store_true",
        help="Exit non-zero when inconsistencies exist",
    )

    repair_parser = sub.add_parser("repair", help="Repair one user via write gateway")
    repair_parser.add_argument("--username")
    repair_parser.add_argument("--user-id", type=int)
    repair_parser.add_argument(
        "--staging-validated",
        action="store_true",
        required=True,
        help="Confirm staging/pre-release validation completed",
    )
    repair_parser.add_argument(
        "--validation-ref",
        help="Ticket/change id from staging validation",
    )
    repair_parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Run pre-audit only; do not mutate data",
    )

    args = parser.parse_args(argv)
    session = SessionLocal()
    try:
        if args.command == "audit":
            issues = audit_user_llm_consistency(session)
            print(format_audit_report(issues))
            if issues and args.fail_on_issues:
                return 1
            return 0

        result = run_dba_user_llm_script(
            session,
            lambda db: _repair_action(
                db,
                username=args.username,
                user_id=args.user_id,
            ),
            staging_validated=args.staging_validated,
            validation_ref=args.validation_ref,
            apply=not args.dry_run,
        )
        logger.info(
            "DBA repair complete applied=%s pre=%d post=%d",
            result.applied,
            len(result.pre_issues),
            len(result.post_issues),
        )
        return 0
    except DBAUserLLMValidationError as exc:
        logger.error("%s", exc)
        session.rollback()
        return 1
    except Exception:
        session.rollback()
        logger.exception("DBA User LLM runner failed")
        raise
    finally:
        session.close()


if __name__ == "__main__":
    sys.exit(main())
