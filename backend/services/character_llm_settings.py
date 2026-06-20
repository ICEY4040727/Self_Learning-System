"""Helpers for role-specific LLM settings stored on Character rows."""

from __future__ import annotations

from typing import Any

from backend.models.models import Character, User
from backend.services.user_llm_settings import get_effective_llm_config


def normalize_character_llm_settings(settings: dict[str, Any] | None) -> dict[str, Any] | None:
    if not isinstance(settings, dict):
        return None

    normalized: dict[str, Any] = {}

    provider = settings.get("provider")
    if isinstance(provider, str) and provider.strip():
        normalized["provider"] = provider.strip()

    model = settings.get("model")
    if isinstance(model, str) and model.strip():
        normalized["model"] = model.strip()

    base_url = settings.get("base_url")
    if isinstance(base_url, str) and base_url.strip():
        normalized["base_url"] = base_url.strip()

    temperature = settings.get("temperature")
    if isinstance(temperature, (int, float)):
        normalized["temperature"] = float(temperature)

    max_tokens = settings.get("max_tokens")
    if isinstance(max_tokens, int):
        normalized["max_tokens"] = max_tokens

    return normalized or None


def get_character_llm_overrides(character: Character | None) -> dict[str, Any]:
    if not character or not isinstance(character.llm_settings, dict):
        return {}
    return normalize_character_llm_settings(character.llm_settings) or {}


def get_effective_character_llm_config(
    user: User,
    character: Character | None = None,
) -> Any:
    overrides = get_character_llm_overrides(character)
    return get_effective_llm_config(
        user,
        provider=overrides.get("provider"),
        model=overrides.get("model"),
        base_url=overrides.get("base_url"),
        temperature=overrides.get("temperature"),
        max_tokens=overrides.get("max_tokens"),
    )
