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

    # Save directory (used by save_file_manager)
    save_directory: str = "./saves"

    # Application version (single source of truth)
    app_version: str = "1.0.0"

    # Learning system tunable parameters
    learning_system: dict = {
        "memory": {
            "dedup_window_hours": 24,
            "max_working_context_tokens": 4000,
            "max_working_context_messages": 50,
            "salience_base_decay": 0.1,
            "salience_recall_factor": 0.5,
            "default_retrieve_limit": 10,
            "observe_recent_limit": 20,
        },
        "profile": {
            "hallucination_guard_min_facts": 3,
            "strength_threshold": 0.7,
            "weakness_threshold": 0.4,
        },
        "extraction": {
            "channel2_enabled": True,
            "confusion_keywords": ["不懂", "没看明白", "什么意思", "不理解", "不明白"],
            "mastery_keywords": ["明白了", "懂了", "原来如此", "学会了", "理解了"],
            "emotion_negative_keywords": ["好难", "崩溃", "累了", "头疼", "放弃"],
            "preference_keywords": {
                "example_first": ["举个例子", "能举个例子吗", "比如呢"],
                "step_by_step": ["详细步骤", "一步一步", "能详细讲讲步骤吗"],
            },
            "confusion_question_mark_threshold": 0.3,
        },
        "salience_type_multiplier": {
            "concept_struggle": 0.0,
            "concept_mastered": 0.3,
            "preference": 0.0,
            "student_state": 1.5,
            "event": 0.8,
            "commitment": 0.5,
        },
        # [TODO-T9] mastery_tracker / teaching_planner tunables
        "mastery": {
            "delta_map": {
                "concept_mastered": 25,
                "concept_struggle": -15,
                "student_state": 0,
                "preference": 0,
                "event": 0,
                "commitment": 0,
            },
            "min": 0,
            "max": 100,
            "auto_advance_threshold": 70,
            "weak_threshold": 40,
            "lesson_started_initial": 20,
        },
    }

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
