"""User-level LLM provider settings helpers.

The legacy user columns are kept as a compatibility mirror for the active
provider. The provider-specific JSON column is the source for remembering
separate key/model/base URL values per provider.

Write gateway (mandatory):
    All mutations to User LLM columns MUST go through this module.
    Business routes, offline scripts, and data-repair jobs must call
    ``update_provider_settings()`` / ``update_generation_params()`` here;
    direct ORM assignment elsewhere is forbidden (see CONTRIBUTING.md).
"""

from __future__ import annotations

import logging
import os
import threading
from contextlib import nullcontext
from dataclasses import dataclass
from typing import Any

from sqlalchemy.orm import Session, object_session

from backend.core.security import decrypt_api_key, encrypt_api_key
from backend.models.models import User
from backend.services.user_llm_telemetry import (
    log_gateway_write,
    log_read_heal_backfill,
    log_read_heal_failed,
    log_read_heal_persist,
)
from backend.services.user_llm_write_guard import authorized_user_llm_write

logger = logging.getLogger("user_llm.settings")

DEFAULT_PROVIDER = "claude"
DEFAULT_TEMPERATURE = 0.7
DEFAULT_MAX_TOKENS = 2048

_backfill_inflight: set[tuple[int, str]] = set()
_backfill_lock = threading.Lock()


def lock_user_for_update(session: Session, user_id: int) -> User:
    """Pessimistic row lock for User LLM settings read-modify-write."""
    return session.query(User).filter(User.id == user_id).with_for_update().one()


@dataclass(frozen=True)
class LegacyBackfill:
    """Legacy mirror values merged into a JSON entry during read."""

    provider: str
    encrypted_api_key: str | None = None
    model: str | None = None
    base_url: str | None = None

    @property
    def has_backfill(self) -> bool:
        return bool(self.encrypted_api_key or self.model or self.base_url)

    @property
    def field_names(self) -> list[str]:
        names: list[str] = []
        if self.encrypted_api_key:
            names.append("encrypted_api_key")
        if self.model:
            names.append("model")
        if self.base_url:
            names.append("base_url")
        return names


@dataclass(frozen=True)
class EffectiveLLMConfig:
    provider: str
    api_key: str | None
    api_key_configured: bool
    model: str | None
    base_url: str | None
    temperature: float
    max_tokens: int


def normalize_provider(provider: str | None) -> str:
    normalized = (provider or "").strip()
    return normalized or DEFAULT_PROVIDER


def normalize_base_url(provider: str, base_url: str | None) -> str | None:
    if not base_url:
        return None

    normalized = base_url.strip().split("?", 1)[0].split("#", 1)[0].rstrip("/")
    if not normalized:
        return None

    lowered = normalized.lower()
    if provider == "local":
        suffix = "/api/chat"
        return normalized[: -len(suffix)] if lowered.endswith(suffix) else normalized

    marker = "/v1/"
    if marker in lowered:
        return normalized[: lowered.index(marker) + len("/v1")]
    return normalized if lowered.endswith("/v1") else f"{normalized}/v1"


def _raw_provider_settings(user: User) -> dict[str, Any]:
    raw = getattr(user, "llm_provider_settings", None)
    return raw if isinstance(raw, dict) else {}


def _entry_with_legacy_backfill(
    user: User,
    provider: str,
    *,
    include_legacy: bool = True,
) -> tuple[dict[str, Any], LegacyBackfill | None]:
    settings_map = _raw_provider_settings(user)
    raw_entry = settings_map.get(provider, {})
    entry = dict(raw_entry) if isinstance(raw_entry, dict) else {}
    backfill: LegacyBackfill | None = None

    if include_legacy and provider == normalize_provider(user.default_provider):
        encrypted_api_key = None
        model = None
        base_url = None
        if not entry.get("encrypted_api_key") and user.encrypted_api_key:
            entry["encrypted_api_key"] = user.encrypted_api_key
            encrypted_api_key = user.encrypted_api_key
        if not entry.get("model") and user.model:
            entry["model"] = user.model
            model = user.model
        if not entry.get("base_url") and user.llm_base_url:
            entry["base_url"] = user.llm_base_url
            base_url = user.llm_base_url
        if encrypted_api_key or model or base_url:
            backfill = LegacyBackfill(
                provider=provider,
                encrypted_api_key=encrypted_api_key,
                model=model,
                base_url=base_url,
            )

    return entry, backfill


def _entry_for_provider(user: User, provider: str, include_legacy: bool = True) -> dict[str, Any]:
    entry, _ = _entry_with_legacy_backfill(user, provider, include_legacy=include_legacy)
    return entry


def _legacy_backfill_for_provider(user: User, provider: str) -> LegacyBackfill | None:
    _, backfill = _entry_with_legacy_backfill(user, provider, include_legacy=True)
    return backfill


def _persist_provider_json_backfill(session: Session, user: User, backfill: LegacyBackfill) -> bool:
    """Persist legacy fallback values into JSON via the write gateway."""
    current = _legacy_backfill_for_provider(user, backfill.provider)
    if current is None:
        return False

    with session.no_autoflush, authorized_user_llm_write(
        source="persist_legacy_backfill",
        user_id=user.id,
        session=session,
    ) as trace_id:
        settings_map = {
            key: dict(value)
            for key, value in _raw_provider_settings(user).items()
            if isinstance(value, dict)
        }
        entry = dict(settings_map.get(backfill.provider, {}))
        if current.encrypted_api_key:
            entry["encrypted_api_key"] = current.encrypted_api_key
        if current.model:
            entry["model"] = current.model
        if current.base_url:
            entry["base_url"] = current.base_url
        settings_map[backfill.provider] = entry
        user.llm_provider_settings = settings_map

        if backfill.provider == normalize_provider(user.default_provider):
            user.default_provider = backfill.provider
            user.encrypted_api_key = entry.get("encrypted_api_key")
            user.model = entry.get("model")
            user.llm_base_url = entry.get("base_url")

    log_gateway_write(
        source="persist_legacy_backfill",
        trace_id=trace_id,
        user_id=user.id,
        provider=backfill.provider,
        fields=["llm_provider_settings", *current.field_names],
        dual_write=True,
    )
    return True


def persist_legacy_backfill(user_id: int, provider: str) -> bool:
    """Open a standalone session and persist any remaining legacy fallback values."""
    from backend.db.database import SessionLocal

    session = SessionLocal()
    try:
        user = session.get(User, user_id)
        if user is None:
            return False
        backfill = _legacy_backfill_for_provider(user, provider)
        if backfill is None:
            return False
        if not _persist_provider_json_backfill(session, user, backfill):
            return False
        session.commit()
        log_read_heal_persist(
            user_id=user_id,
            provider=provider,
            fields=backfill.field_names,
            async_mode=False,
        )
        return True
    except Exception as exc:
        session.rollback()
        log_read_heal_failed(user_id=user_id, provider=provider, error=str(exc))
        logger.warning(
            "Legacy backfill persist failed for user_id=%s provider=%s",
            user_id,
            provider,
            exc_info=True,
        )
        return False
    finally:
        session.close()


def _schedule_legacy_backfill_persist(user_id: int, backfill: LegacyBackfill) -> None:
    if not backfill.has_backfill:
        return

    inflight_key = (user_id, backfill.provider)
    with _backfill_lock:
        if inflight_key in _backfill_inflight:
            return
        _backfill_inflight.add(inflight_key)

    def _run() -> None:
        try:
            persist_legacy_backfill(user_id, backfill.provider)
        finally:
            with _backfill_lock:
                _backfill_inflight.discard(inflight_key)

    if os.environ.get("TESTING") == "1":
        _run()
        return

    thread = threading.Thread(target=_run, name=f"user-llm-read-heal-{user_id}", daemon=True)
    thread.start()


def _decrypt_key(encrypted_api_key: str | None) -> str | None:
    if not encrypted_api_key:
        return None
    try:
        return decrypt_api_key(encrypted_api_key)
    except Exception:
        return None


def get_effective_llm_config(
    user: User,
    provider: str | None = None,
    api_key: str | None = None,
    model: str | None = None,
    base_url: str | None = None,
    temperature: float | None = None,
    max_tokens: int | None = None,
    *,
    auto_persist_legacy_backfill: bool = True,
) -> EffectiveLLMConfig:
    active_provider = normalize_provider(provider or user.default_provider)
    entry, legacy_backfill = _entry_with_legacy_backfill(user, active_provider)

    submitted_key = api_key.strip() if api_key and api_key.strip() else None
    stored_key = _decrypt_key(entry.get("encrypted_api_key"))
    resolved_key = submitted_key or stored_key

    resolved_model = model.strip() if model is not None and model.strip() else entry.get("model")
    raw_base_url = base_url if base_url is not None and base_url.strip() else entry.get("base_url")
    resolved_base_url = normalize_base_url(active_provider, raw_base_url)

    resolved_temperature = (
        temperature
        if temperature is not None
        else (user.temperature if user.temperature is not None else DEFAULT_TEMPERATURE)
    )
    resolved_max_tokens = (
        max_tokens
        if max_tokens is not None
        else (user.max_tokens if user.max_tokens is not None else DEFAULT_MAX_TOKENS)
    )

    if legacy_backfill is not None:
        log_read_heal_backfill(
            user_id=user.id,
            provider=legacy_backfill.provider,
            fields=legacy_backfill.field_names,
        )
        if auto_persist_legacy_backfill:
            _schedule_legacy_backfill_persist(user.id, legacy_backfill)

    return EffectiveLLMConfig(
        provider=active_provider,
        api_key=resolved_key,
        api_key_configured=bool(resolved_key),
        model=resolved_model,
        base_url=resolved_base_url,
        temperature=resolved_temperature,
        max_tokens=resolved_max_tokens,
    )


def update_generation_params(
    user: User,
    *,
    temperature: float | None = None,
    max_tokens: int | None = None,
) -> None:
    """Update user-level generation params (not provider-specific)."""
    session = object_session(user)
    fields: list[str] = []
    if temperature is not None:
        fields.append("temperature")
    if max_tokens is not None:
        fields.append("max_tokens")

    flush_ctx = session.no_autoflush if session is not None else nullcontext()
    with flush_ctx, authorized_user_llm_write(
        source="update_generation_params",
        user_id=user.id,
        session=session,
    ) as trace_id:
        if temperature is not None:
            user.temperature = temperature
        if max_tokens is not None:
            user.max_tokens = max_tokens

    if fields:
        log_gateway_write(
            source="update_generation_params",
            trace_id=trace_id,
            user_id=user.id,
            fields=fields,
            dual_write=False,
        )


def update_provider_settings(
    user: User,
    provider: str | None,
    *,
    api_key: str | None = None,
    clear_api_key: bool = False,
    model: str | None = None,
    base_url: str | None = None,
) -> None:
    active_provider = normalize_provider(provider or user.default_provider)
    session = object_session(user)
    fields: list[str] = ["llm_provider_settings", "default_provider"]
    if api_key is not None or clear_api_key:
        fields.append("encrypted_api_key")
    if model is not None:
        fields.append("model")
    if base_url is not None:
        fields.append("llm_base_url")

    flush_ctx = session.no_autoflush if session is not None else nullcontext()
    with flush_ctx, authorized_user_llm_write(
        source="update_provider_settings",
        user_id=user.id,
        session=session,
    ) as trace_id:
        settings_map = {
            key: dict(value)
            for key, value in _raw_provider_settings(user).items()
            if isinstance(value, dict)
        }
        entry = dict(settings_map.get(active_provider, {}))

        if clear_api_key:
            entry.pop("encrypted_api_key", None)

        submitted_key = api_key.strip() if api_key and api_key.strip() else None
        if submitted_key:
            entry["encrypted_api_key"] = encrypt_api_key(submitted_key)

        if model is not None:
            cleaned_model = model.strip()
            if cleaned_model:
                entry["model"] = cleaned_model
            else:
                entry.pop("model", None)

        if base_url is not None:
            cleaned_base_url = normalize_base_url(active_provider, base_url)
            if cleaned_base_url:
                entry["base_url"] = cleaned_base_url
            else:
                entry.pop("base_url", None)

        if entry:
            settings_map[active_provider] = entry
        else:
            settings_map.pop(active_provider, None)

        user.llm_provider_settings = settings_map

        # Compatibility mirror for code or old clients that still read the legacy
        # top-level columns.
        user.default_provider = active_provider
        user.encrypted_api_key = entry.get("encrypted_api_key")
        user.model = entry.get("model")
        user.llm_base_url = entry.get("base_url")

    log_gateway_write(
        source="update_provider_settings",
        trace_id=trace_id,
        user_id=user.id,
        provider=active_provider,
        fields=fields,
        dual_write=True,
    )


def serialize_provider_settings(user: User) -> dict[str, dict[str, Any]]:
    providers = set(_raw_provider_settings(user).keys())
    providers.add(normalize_provider(user.default_provider))

    result: dict[str, dict[str, Any]] = {}
    for provider in sorted(providers):
        entry = _entry_for_provider(user, provider)
        if not entry:
            continue
        result[provider] = {
            "api_key_configured": bool(entry.get("encrypted_api_key")),
            "model": entry.get("model"),
            "base_url": entry.get("base_url"),
        }
    return result
