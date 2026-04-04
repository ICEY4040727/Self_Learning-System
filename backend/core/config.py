import warnings
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict

_DEFAULT_SECRET = "your-secret-key-change-in-production"


class Settings(BaseSettings):
    # Database (SQLite single file)
    database_url: str = "sqlite:///./data/socratic_learning.db"

    # CORS
    cors_origin: str = "http://localhost:5173"

    # JWT
    secret_key: str = _DEFAULT_SECRET
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 60 * 24  # 24 hours

    # LLM Configuration
    llm_default_provider: str = "claude"
    llm_providers: dict = {
        "claude": {
            "enabled": True,
            "api_key": "",
            "model": "claude-3-5-sonnet-20241022"
        },
        "openai": {
            "enabled": False,
            "api_key": "",
            "model": "gpt-4"
        }
    }

    # Sentry
    sentry_dsn: str = ""

    # Features
    features_voice_enabled: bool = False

    # Save directory
    save_directory: str = "./saves"

    model_config = SettingsConfigDict(
        env_file=".env",
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    s = Settings()
    if s.secret_key == _DEFAULT_SECRET:
        warnings.warn(
            "Using default SECRET_KEY! Set SECRET_KEY in .env for production.",
            stacklevel=2,
        )
    return s
