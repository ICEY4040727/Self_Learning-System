"""Audit JSON primary storage vs legacy mirror columns on users."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import Session

from backend.models.models import User
from backend.services.user_llm_settings import normalize_provider

LEGACY_MIRROR_FIELDS = (
    ("encrypted_api_key", "encrypted_api_key"),
    ("model", "model"),
    ("llm_base_url", "base_url"),
)


@dataclass(frozen=True)
class UserLLMInconsistency:
    user_id: int
    username: str
    field: str
    legacy_value: Any
    json_value: Any
    message: str


def _json_entry(user: User, provider: str) -> dict[str, Any]:
    raw = user.llm_provider_settings
    if not isinstance(raw, dict):
        return {}
    entry = raw.get(provider)
    return dict(entry) if isinstance(entry, dict) else {}


def audit_user_llm_consistency(session: Session) -> list[UserLLMInconsistency]:
    """Return active-provider legacy/json mismatches for all users."""
    issues: list[UserLLMInconsistency] = []

    for user in session.query(User).order_by(User.id).all():
        active_provider = normalize_provider(user.default_provider)
        entry = _json_entry(user, active_provider)

        if user.default_provider != active_provider:
            issues.append(
                UserLLMInconsistency(
                    user_id=user.id,
                    username=user.username,
                    field="default_provider",
                    legacy_value=user.default_provider,
                    json_value=active_provider,
                    message="default_provider empty/invalid; normalized active provider differs",
                )
            )

        for legacy_field, json_field in LEGACY_MIRROR_FIELDS:
            legacy_value = getattr(user, legacy_field)
            json_value = entry.get(json_field)
            if legacy_value != json_value:
                issues.append(
                    UserLLMInconsistency(
                        user_id=user.id,
                        username=user.username,
                        field=legacy_field,
                        legacy_value=legacy_value,
                        json_value=json_value,
                        message=(
                            f"legacy `{legacy_field}` does not match "
                            f"llm_provider_settings[{active_provider!r}].{json_field}"
                        ),
                    )
                )

    return issues


def audit_user_llm_consistency_sql(session: Session) -> list[UserLLMInconsistency]:
    """SQL full-table scan (PostgreSQL). Falls back to ORM audit on other dialects."""
    dialect = session.get_bind().dialect.name
    if dialect != "postgresql":
        return audit_user_llm_consistency(session)

    rows = session.execute(
        text(
            """
            WITH active AS (
                SELECT
                    id,
                    username,
                    COALESCE(NULLIF(default_provider, ''), 'claude') AS provider,
                    default_provider,
                    encrypted_api_key,
                    model,
                    llm_base_url,
                    llm_provider_settings
                FROM users
            )
            SELECT
                id,
                username,
                'model' AS field,
                model AS legacy_value,
                llm_provider_settings -> provider ->> 'model' AS json_value
            FROM active
            WHERE model IS DISTINCT FROM (llm_provider_settings -> provider ->> 'model')
            UNION ALL
            SELECT
                id,
                username,
                'llm_base_url' AS field,
                llm_base_url AS legacy_value,
                llm_provider_settings -> provider ->> 'base_url' AS json_value
            FROM active
            WHERE llm_base_url IS DISTINCT FROM (llm_provider_settings -> provider ->> 'base_url')
            UNION ALL
            SELECT
                id,
                username,
                'encrypted_api_key' AS field,
                encrypted_api_key AS legacy_value,
                llm_provider_settings -> provider ->> 'encrypted_api_key' AS json_value
            FROM active
            WHERE encrypted_api_key IS DISTINCT FROM (
                llm_provider_settings -> provider ->> 'encrypted_api_key'
            )
            ORDER BY id, field
            """
        )
    ).mappings()

    return [
        UserLLMInconsistency(
            user_id=row["id"],
            username=row["username"],
            field=row["field"],
            legacy_value=row["legacy_value"],
            json_value=row["json_value"],
            message=f"SQL scan: legacy `{row['field']}` != JSON mirror",
        )
        for row in rows
    ]


def count_legacy_backfill_candidates(session: Session) -> int:
    """Users whose active-provider JSON is missing values still present on legacy columns."""
    count = 0
    for user in session.query(User).order_by(User.id).all():
        active_provider = normalize_provider(user.default_provider)
        entry = _json_entry(user, active_provider)
        needs_backfill = False
        if user.encrypted_api_key and not entry.get("encrypted_api_key"):
            needs_backfill = True
        if user.model and not entry.get("model"):
            needs_backfill = True
        if user.llm_base_url and not entry.get("base_url"):
            needs_backfill = True
        if needs_backfill:
            count += 1
    return count


def format_audit_report(issues: list[UserLLMInconsistency]) -> str:
    if not issues:
        return "OK: all users have consistent legacy/json LLM settings."

    lines = [f"Found {len(issues)} User LLM consistency issue(s):"]
    for issue in issues:
        lines.append(
            f"- user_id={issue.user_id} username={issue.username!r} "
            f"field={issue.field} legacy={issue.legacy_value!r} json={issue.json_value!r}"
        )
    return "\n".join(lines)
