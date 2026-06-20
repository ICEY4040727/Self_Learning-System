"""Structured logging markers for User LLM write / audit observability.

Grep examples:
  rg "USER_LLM_WRITE" logs/
  rg "USER_LLM_WRITE_BLOCKED" logs/
  rg "USER_LLM_AUDIT" logs/
  rg "USER_LLM_READ_HEAL" logs/
"""
from __future__ import annotations

import logging
from contextvars import ContextVar, Token
from typing import Any
from uuid import uuid4

logger = logging.getLogger("user_llm.telemetry")

MARKER_WRITE = "USER_LLM_WRITE"
MARKER_BLOCKED = "USER_LLM_WRITE_BLOCKED"
MARKER_AUDIT = "USER_LLM_AUDIT"
MARKER_READ_HEAL = "USER_LLM_READ_HEAL"
MARKER_CONFLICT = "USER_LLM_SETTINGS_CONFLICT"

_write_trace_id: ContextVar[str | None] = ContextVar("user_llm_write_trace_id", default=None)
_write_source: ContextVar[str | None] = ContextVar("user_llm_write_source", default=None)


def current_write_trace_id() -> str | None:
    return _write_trace_id.get()


def current_write_source() -> str | None:
    return _write_source.get()


def begin_write_trace(*, source: str) -> tuple[str, Token, Token]:
    trace_id = uuid4().hex[:12]
    auth_token = _write_trace_id.set(trace_id)
    source_token = _write_source.set(source)
    logger.info(
        "[%s] event=gateway_enter source=%s trace_id=%s",
        MARKER_WRITE,
        source,
        trace_id,
    )
    return trace_id, auth_token, source_token


def end_write_trace(auth_token: Token, source_token: Token) -> None:
    _write_trace_id.reset(auth_token)
    _write_source.reset(source_token)


def log_gateway_write(
    *,
    source: str,
    trace_id: str,
    user_id: int | None,
    provider: str | None = None,
    fields: list[str] | None = None,
    dual_write: bool = True,
) -> None:
    logger.info(
        "[%s] event=gateway_write source=%s trace_id=%s user_id=%s provider=%s "
        "fields=%s dual_write=%s",
        MARKER_WRITE,
        source,
        trace_id,
        user_id,
        provider,
        ",".join(fields or []),
        dual_write,
    )


def log_blocked_write(
    *,
    user_id: int | None,
    field: str,
    via: str,
    trace_id: str | None = None,
) -> None:
    logger.warning(
        "[%s] event=blocked_write user_id=%s field=%s via=%s trace_id=%s "
        "hint=no_gateway_marker_likely_raw_write",
        MARKER_BLOCKED,
        user_id,
        field,
        via,
        trace_id or current_write_trace_id(),
    )


def log_audit_issues(issues: list[Any]) -> None:
    if not issues:
        logger.info("[%s] event=scan_ok issue_count=0", MARKER_AUDIT)
        return

    logger.warning(
        "[%s] event=scan_dirty issue_count=%d",
        MARKER_AUDIT,
        len(issues),
    )
    for issue in issues:
        logger.warning(
            "[%s] event=dirty_row user_id=%s username=%s field=%s legacy=%r json=%r message=%s",
            MARKER_AUDIT,
            getattr(issue, "user_id", None),
            getattr(issue, "username", None),
            getattr(issue, "field", None),
            getattr(issue, "legacy_value", None),
            getattr(issue, "json_value", None),
            getattr(issue, "message", None),
        )


def log_repair_start(*, user_count: int) -> None:
    logger.info("[%s] event=repair_start user_count=%d", MARKER_AUDIT, user_count)


def log_repair_success(*, user_id: int, username: str) -> None:
    logger.info(
        "[%s] event=repair_ok user_id=%s username=%s",
        MARKER_AUDIT,
        user_id,
        username,
    )


def log_repair_failure(*, user_id: int, username: str, error: str) -> None:
    logger.error(
        "[%s] event=repair_failed user_id=%s username=%s error=%s",
        MARKER_AUDIT,
        user_id,
        username,
        error,
    )


def log_patrol_failed(*, reason: str, detail: str = "") -> None:
    logger.error(
        "[%s] event=patrol_failed reason=%s %s",
        MARKER_AUDIT,
        reason,
        detail.strip(),
    )


def log_read_heal_persist(
    *,
    user_id: int,
    provider: str,
    fields: list[str],
    async_mode: bool,
) -> None:
    logger.info(
        "[%s] event=legacy_backfill_persist user_id=%s provider=%s fields=%s async=%s",
        MARKER_READ_HEAL,
        user_id,
        provider,
        ",".join(fields),
        async_mode,
    )


def log_read_heal_failed(*, user_id: int, provider: str, error: str) -> None:
    logger.warning(
        "[%s] event=legacy_backfill_failed user_id=%s provider=%s error=%s",
        MARKER_READ_HEAL,
        user_id,
        provider,
        error,
    )


def log_read_heal_backfill(
    *,
    user_id: int,
    provider: str,
    fields: list[str],
) -> None:
    """Read path used legacy mirror values because JSON entry was incomplete."""
    logger.info(
        "[%s] event=legacy_backfill_read user_id=%s provider=%s fields=%s",
        MARKER_READ_HEAL,
        user_id,
        provider,
        ",".join(fields),
    )


def log_settings_conflict(
    *,
    user_id: int,
    expected_version: int,
    current_version: int | None = None,
    via: str = "api",
) -> None:
    logger.warning(
        "[%s] event=optimistic_lock_conflict user_id=%s expected_version=%s "
        "current_version=%s via=%s",
        MARKER_CONFLICT,
        user_id,
        expected_version,
        current_version,
        via,
    )


def log_patrol_metrics(
    *,
    pre_issue_count: int,
    post_issue_count: int,
    legacy_backfill_candidate_count: int,
    repaired_user_count: int,
    repair_error_count: int,
    applied_repair: bool,
    exit_code: int,
) -> None:
    logger.info(
        "[%s] event=patrol_metrics pre_issues=%d post_issues=%d "
        "legacy_backfill_candidates=%d repaired_users=%d repair_errors=%d "
        "applied_repair=%s exit_code=%d",
        MARKER_AUDIT,
        pre_issue_count,
        post_issue_count,
        legacy_backfill_candidate_count,
        repaired_user_count,
        repair_error_count,
        applied_repair,
        exit_code,
    )
