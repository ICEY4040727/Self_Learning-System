from datetime import UTC, datetime
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Response, UploadFile
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import func as sa_func
from sqlalchemy.orm import Session
from sqlalchemy.orm.exc import StaleDataError

from backend.api.routes.auth import get_current_user
from backend.db.database import get_db
from backend.models import models as models_module
from backend.models.models import User
from backend.core.conflicts.user_llm_settings import raise_settings_conflict_http
from backend.services.user_llm_settings import (
    get_effective_llm_config,
    lock_user_for_update,
    normalize_base_url,
    serialize_provider_settings,
    update_generation_params,
    update_provider_settings,
)


router = APIRouter()

# Settings endpoints
class SettingsUpdate(BaseModel):
    version: int = Field(..., ge=0)
    default_provider: str | None = None
    api_key: str | None = None
    clear_api_key: bool = False
    temperature: float | None = Field(default=None, ge=0, le=2)
    max_tokens: int | None = Field(default=None, ge=1, le=200000)
    model: str | None = None
    base_url: str | None = None


class SettingsResponse(BaseModel):
    version: int
    default_provider: str | None = None
    api_key_configured: bool = False
    temperature: float | None = None
    max_tokens: int | None = None
    model: str | None = None
    base_url: str | None = None
    provider_settings: dict[str, dict[str, str | bool | None]] = Field(default_factory=dict)


class SettingsTestRequest(BaseModel):
    default_provider: str | None = None
    api_key: str | None = None
    temperature: float | None = Field(default=None, ge=0, le=2)
    max_tokens: int | None = Field(default=None, ge=1, le=200000)
    model: str | None = None
    base_url: str | None = None


class SettingsTestResponse(BaseModel):
    ok: bool
    provider: str
    model: str | None = None
    base_url: str | None = None
    message: str


class SettingsModelsRequest(BaseModel):
    default_provider: str | None = None
    api_key: str | None = None
    model: str | None = None
    base_url: str | None = None


class SettingsModelsResponse(BaseModel):
    provider: str
    base_url: str | None = None
    source: str
    models: list[str] = Field(default_factory=list)
    message: str | None = None


def _normalize_settings_base_url(provider: str, base_url: str | None) -> str | None:
    return normalize_base_url(provider, base_url)


def _fallback_settings_models(provider: str) -> list[str]:
    from backend.services.llm.models import (
        CLAUDE_MODELS,
        OPENAI_COMPATIBLE_MODELS,
        OPENAI_MODELS,
        OLLAMA_MODELS,
    )

    if provider == "claude":
        return list(CLAUDE_MODELS.keys())
    if provider == "openai":
        return list(OPENAI_MODELS.keys())
    if provider == "local":
        return list(OLLAMA_MODELS.keys())
    return list(OPENAI_COMPATIBLE_MODELS.keys())


@router.get("/settings", response_model=SettingsResponse)
def get_settings(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    active = get_effective_llm_config(current_user)
    return SettingsResponse(
        version=current_user.version,
        default_provider=active.provider,
        api_key_configured=active.api_key_configured,
        temperature=active.temperature,
        max_tokens=active.max_tokens,
        model=active.model,
        base_url=active.base_url,
        provider_settings=serialize_provider_settings(current_user),
    )


@router.put("/settings")
def update_settings(
    settings: SettingsUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    user = lock_user_for_update(db, current_user.id)

    if user.version != settings.version:
        raise_settings_conflict_http(
            user_id=user.id,
            expected_version=settings.version,
            current_version=user.version,
        )

    target_provider = settings.default_provider or user.default_provider or "claude"

    try:
        with db.no_autoflush:
            update_generation_params(
                user,
                temperature=settings.temperature,
                max_tokens=settings.max_tokens,
            )

            update_provider_settings(
                user,
                target_provider,
                api_key=settings.api_key,
                clear_api_key=settings.clear_api_key,
                model=settings.model,
                base_url=settings.base_url,
            )

        db.commit()
        db.refresh(user)
    except StaleDataError:
        db.rollback()
        raise_settings_conflict_http(
            user_id=user.id,
            expected_version=settings.version,
            via="commit_race",
        )

    return {"message": "Settings updated", "version": user.version}


@router.post("/settings/test-connection", response_model=SettingsTestResponse)
async def test_settings_connection(
    settings: SettingsTestRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    config = get_effective_llm_config(
        current_user,
        provider=settings.default_provider,
        api_key=settings.api_key,
        model=settings.model,
        base_url=settings.base_url,
        temperature=settings.temperature,
        max_tokens=settings.max_tokens,
    )

    from backend.services.llm.providers import provider_needs_api_key
    if provider_needs_api_key(config.provider) and not config.api_key:
        return SettingsTestResponse(
            ok=False,
            provider=config.provider,
            model=config.model,
            base_url=config.base_url,
            message="API Key is not configured for this provider.",
        )

    try:
        from backend.services.llm.manager import get_llm_manager

        adapter = get_llm_manager().get_adapter(
            provider=config.provider,
            model=config.model,
            api_key=config.api_key,
            base_url=config.base_url,
        )
        await adapter.chat(
            messages=[{"role": "user", "content": "ping"}],
            system_prompt="Reply with a short ok.",
            user_api_key=config.api_key,
            temperature=config.temperature,
            max_tokens=min(config.max_tokens, 32),
        )
    except Exception as exc:
        return SettingsTestResponse(
            ok=False,
            provider=config.provider,
            model=config.model,
            base_url=config.base_url,
            message=f"{type(exc).__name__}: {str(exc)[:300]}",
        )

    return SettingsTestResponse(
        ok=True,
        provider=config.provider,
        model=config.model,
        base_url=config.base_url,
        message="Connection test succeeded.",
    )


@router.post("/settings/models", response_model=SettingsModelsResponse)
async def list_settings_models(
    settings: SettingsModelsRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    config = get_effective_llm_config(
        current_user,
        provider=settings.default_provider,
        api_key=settings.api_key,
        model=settings.model,
        base_url=settings.base_url,
    )

    if config.provider == "local":
        return SettingsModelsResponse(
            provider=config.provider,
            base_url=config.base_url,
            source="preset",
            models=_fallback_settings_models(config.provider),
            message="Local provider uses preset model suggestions.",
        )

    try:
        from backend.services.llm.manager import get_llm_manager
        from backend.services.llm.providers import provider_needs_api_key

        if provider_needs_api_key(config.provider) and not config.api_key:
            return SettingsModelsResponse(
                provider=config.provider,
                base_url=config.base_url,
                source="preset",
                models=_fallback_settings_models(config.provider),
                message="API Key is not configured; showing preset model suggestions.",
            )

        adapter = get_llm_manager().get_adapter(
            provider=config.provider,
            model=config.model,
            api_key=config.api_key,
            base_url=config.base_url,
        )
        remote_models = await adapter.list_models(user_api_key=config.api_key)
        if remote_models:
            return SettingsModelsResponse(
                provider=config.provider,
                base_url=config.base_url,
                source="remote",
                models=remote_models,
                message="Fetched models from gateway.",
            )
        return SettingsModelsResponse(
            provider=config.provider,
            base_url=config.base_url,
            source="preset",
            models=_fallback_settings_models(config.provider),
            message="Gateway returned no models; showing preset suggestions.",
        )
    except Exception as exc:
        return SettingsModelsResponse(
            provider=config.provider,
            base_url=config.base_url,
            source="fallback",
            models=_fallback_settings_models(config.provider),
            message=f"{type(exc).__name__}: {str(exc)[:300]}",
        )
