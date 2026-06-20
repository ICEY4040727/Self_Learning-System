"""ORM runtime guard for User LLM column writes.

All mutations to User LLM fields must occur inside ``authorized_user_llm_write()``.
The write gateway in ``user_llm_settings`` enters that context automatically.

Guards:
  - column ``set`` listeners block unauthorized instance attribute writes
  - ``do_orm_execute`` blocks unauthorized ORM bulk UPDATE on User

Tests set ``TESTING=1`` to disable the guard so fixtures may assign directly.
"""
from __future__ import annotations

import os
from contextlib import contextmanager
from contextvars import ContextVar, Token
from typing import Iterator

from sqlalchemy import event, text
from sqlalchemy.orm import Session

from backend.services.user_llm_telemetry import (
    begin_write_trace,
    end_write_trace,
    log_blocked_write,
)

USER_LLM_WRITE_ATTRS = frozenset({
    "default_provider",
    "encrypted_api_key",
    "llm_provider_settings",
    "llm_base_url",
    "temperature",
    "max_tokens",
    "model",
})

WRITE_TRACE_SETTING = "app.user_llm_write_trace"

_write_authorized: ContextVar[bool] = ContextVar("user_llm_write_authorized", default=False)
_guards_registered = False


class UserLLMWriteForbidden(RuntimeError):
    """Raised when User LLM columns are mutated outside the write gateway."""


def is_user_llm_write_authorized() -> bool:
    return _write_authorized.get()


def is_user_llm_write_guard_enabled() -> bool:
    return os.environ.get("TESTING") != "1"


def _set_db_write_trace(session: Session | None, trace_id: str) -> None:
    if session is None or session.get_bind().dialect.name != "postgresql":
        return
    session.execute(
        text(f"SET LOCAL {WRITE_TRACE_SETTING} = :trace_id"),
        {"trace_id": trace_id},
    )


def _clear_db_write_trace(session: Session | None) -> None:
    if session is None or session.get_bind().dialect.name != "postgresql":
        return
    session.execute(text(f"SET LOCAL {WRITE_TRACE_SETTING} TO DEFAULT"))


@contextmanager
def authorized_user_llm_write(
    *,
    source: str = "unknown",
    user_id: int | None = None,
    session: Session | None = None,
) -> Iterator[str]:
    trace_id, trace_token, source_token = begin_write_trace(source=source)
    auth_token: Token = _write_authorized.set(True)
    _set_db_write_trace(session, trace_id)
    try:
        yield trace_id
    finally:
        _clear_db_write_trace(session)
        _write_authorized.reset(auth_token)
        end_write_trace(trace_token, source_token)


def _require_authorized_write(attr: str, *, via: str, user_id: int | None = None) -> None:
    if not is_user_llm_write_guard_enabled():
        return
    if is_user_llm_write_authorized():
        return
    log_blocked_write(user_id=user_id, field=attr, via=via)
    raise UserLLMWriteForbidden(
        f"Direct ORM write to User.{attr} is forbidden ({via}). "
        "Use backend.services.user_llm_settings.update_* helpers."
    )


def _make_set_listener(attr: str):
    def receive_set(target, value, oldvalue, initiator):  # noqa: ANN001
        user_id = getattr(target, "id", None)
        _require_authorized_write(attr, via="attribute set", user_id=user_id)
        return value

    return receive_set


def _do_orm_execute(execute_state) -> None:  # noqa: ANN001
    if not is_user_llm_write_guard_enabled() or is_user_llm_write_authorized():
        return
    if not execute_state.is_update:
        return

    bind_mapper = execute_state.bind_mapper
    if bind_mapper is None:
        return

    from backend.models.models import User

    if bind_mapper.class_ is not User:
        return

    log_blocked_write(user_id=None, field="*", via="orm bulk update")
    raise UserLLMWriteForbidden(
        "Unauthorized ORM bulk UPDATE on User. "
        "Use backend.services.user_llm_settings.update_* helpers."
    )


def register_user_llm_write_guards() -> None:
    global _guards_registered
    if _guards_registered:
        return

    from backend.models.models import User

    for attr in USER_LLM_WRITE_ATTRS:
        event.listen(getattr(User, attr), "set", _make_set_listener(attr), retval=True)

    event.listen(Session, "do_orm_execute", _do_orm_execute)

    _guards_registered = True
