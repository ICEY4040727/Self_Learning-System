"""User LLM settings optimistic-lock conflict errors."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from fastapi import HTTPException, status


@dataclass(frozen=True)
class UserLLMSettingsConflictError(Exception):
    """Raised when a versioned User LLM settings update loses a race."""

    user_id: int
    expected_version: int
    current_version: int | None = None

    def to_detail(self) -> dict[str, Any]:
        return {
            "code": "user_llm_settings_conflict",
            "message": (
                "Settings were updated elsewhere. Refresh and retry with the latest version."
            ),
            "user_id": self.user_id,
            "expected_version": self.expected_version,
            "current_version": self.current_version,
        }


def raise_settings_conflict_http(
    *,
    user_id: int,
    expected_version: int,
    current_version: int | None = None,
    via: str = "api",
) -> None:
    from backend.services.user_llm_telemetry import log_settings_conflict

    log_settings_conflict(
        user_id=user_id,
        expected_version=expected_version,
        current_version=current_version,
        via=via,
    )
    exc = UserLLMSettingsConflictError(
        user_id=user_id,
        expected_version=expected_version,
        current_version=current_version,
    )
    raise HTTPException(
        status_code=status.HTTP_409_CONFLICT,
        detail=exc.to_detail(),
    )
