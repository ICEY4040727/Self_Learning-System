from pydantic_settings import BaseSettings
from functools import lru_cache
from typing import Optional


class Settings(BaseSettings):
    # Database
    database_url: str = "postgresql://user:password@localhost:5432/socratic_learning"

    # JWT
    secret_key: str = "your-secret-key-change-in-production"
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

    # Features
    features_voice_enabled: bool = False

    # Save directory
    save_directory: str = "./saves"

    class Config:
        env_file = ".env"


@lru_cache
def get_settings() -> Settings:
    return Settings()