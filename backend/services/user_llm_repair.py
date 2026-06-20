"""Batch repair helpers for User LLM JSON/legacy consistency."""
from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy.orm import Session

from backend.models.models import User
from backend.services.user_llm_db_audit import (
    UserLLMInconsistency,
    audit_user_llm_consistency,
    audit_user_llm_consistency_sql,
)
from backend.services.user_llm_db_guard import user_llm_repair_mode
from backend.services.user_llm_settings import (
    get_effective_llm_config,
    lock_user_for_update,
    update_generation_params,
    update_provider_settings,
)
from backend.services.user_llm_telemetry import (
    log_audit_issues,
    log_patrol_failed,
    log_repair_failure,
    log_repair_start,
    log_repair_success,
)


@dataclass(frozen=True)
class UserLLMRepairError:
    user_id: int
    username: str
    error: str


@dataclass(frozen=True)
class UserLLMPatrolResult:
    pre_issues: list[UserLLMInconsistency]
    post_issues: list[UserLLMInconsistency]
    repaired_user_count: int
    repair_errors: list[UserLLMRepairError]
    applied_repair: bool


def repair_user_llm_from_effective_config(session: Session, user: User) -> None:
    """Persist effective config through the write gateway (JSON + legacy mirror)."""
    locked_user = lock_user_for_update(session, user.id)
    config = get_effective_llm_config(locked_user, auto_persist_legacy_backfill=False)
    with session.no_autoflush:
        update_provider_settings(
            locked_user,
            config.provider,
            model=config.model,
            base_url=config.base_url,
        )
        update_generation_params(
            locked_user,
            temperature=config.temperature,
            max_tokens=config.max_tokens,
        )


def patrol_user_llm_consistency(
    session: Session,
    *,
    use_sql: bool = False,
    apply_repair: bool = False,
) -> UserLLMPatrolResult:
    """Scan for JSON/legacy drift; optionally repair all affected users."""
    audit_fn = audit_user_llm_consistency_sql if use_sql else audit_user_llm_consistency

    pre_issues = audit_fn(session)
    log_audit_issues(pre_issues)

    repaired_user_count = 0
    repair_errors: list[UserLLMRepairError] = []

    if apply_repair and pre_issues:
        user_ids = sorted({issue.user_id for issue in pre_issues})
        log_repair_start(user_count=len(user_ids))

        with user_llm_repair_mode(session):
            for user_id in user_ids:
                user = session.get(User, user_id)
                if user is None:
                    repair_errors.append(
                        UserLLMRepairError(
                            user_id=user_id,
                            username="",
                            error="user row missing",
                        )
                    )
                    log_repair_failure(user_id=user_id, username="", error="user row missing")
                    continue

                try:
                    repair_user_llm_from_effective_config(session, user)
                    session.commit()
                    repaired_user_count += 1
                    log_repair_success(user_id=user.id, username=user.username)
                except Exception as exc:
                    session.rollback()
                    repair_errors.append(
                        UserLLMRepairError(
                            user_id=user.id,
                            username=user.username,
                            error=str(exc),
                        )
                    )
                    log_repair_failure(user_id=user.id, username=user.username, error=str(exc))

    post_issues = audit_fn(session)
    if apply_repair:
        log_audit_issues(post_issues)

    return UserLLMPatrolResult(
        pre_issues=pre_issues,
        post_issues=post_issues,
        repaired_user_count=repaired_user_count,
        repair_errors=repair_errors,
        applied_repair=apply_repair,
    )


def patrol_exit_code(
    result: UserLLMPatrolResult,
    *,
    fail_on_issues: bool,
) -> int:
    """Return process exit code for patrol jobs."""
    if result.repair_errors:
        log_patrol_failed(
            reason="repair_errors",
            detail=f"failed_users={len(result.repair_errors)}",
        )
        return 1

    if fail_on_issues and result.post_issues:
        log_patrol_failed(
            reason="remaining_inconsistencies",
            detail=f"issue_count={len(result.post_issues)}",
        )
        return 1

    return 0
