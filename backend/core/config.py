import warnings
from pathlib import Path
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict

_DEFAULT_SECRET = "your-secret-key-change-in-production"


class Settings(BaseSettings):
    # App runtime
    app_host: str = "127.0.0.1"
    app_port: int = 8000
    app_data_dir: str = "./data"

    # Database (SQLite single file unless overridden)
    database_url: str = ""

    # CORS
    cors_origin: str = "http://localhost:5173"
    cors_origins: str = ""

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

    # User LLM patrol alerts (Feishu custom bot webhook)
    user_llm_patrol_alert_webhook: str = ""
    user_llm_patrol_secret: str = ""

    # Features
    features_voice_enabled: bool = False

    # Save directory (used by save_file_manager)
    save_directory: str = ""

    # [TR-X16] Textbook uploads — kept OUTSIDE backend/static so the public
    # /static mount in main.py never serves user-uploaded files. Access goes
    # through the auth-protected GET /api/textbooks/{id}/file endpoint.
    upload_dir: str = ""
    textbook_max_upload_size_bytes: int = 100 * 1024 * 1024

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

    def model_post_init(self, __context) -> None:
        base_data_dir = Path(self.app_data_dir).expanduser().resolve()

        if not self.database_url:
            db_path = (base_data_dir / "socratic_learning.db").as_posix()
            self.database_url = f"sqlite:///{db_path}"

        if not self.save_directory:
            self.save_directory = str((base_data_dir / "saves").resolve())

        if not self.upload_dir:
            self.upload_dir = str((base_data_dir / "uploads").resolve())

    @property
    def cors_allowed_origins(self) -> list[str]:
        raw = self.cors_origins.strip() if self.cors_origins else ""
        if raw:
            return [origin.strip() for origin in raw.split(",") if origin.strip()]
        return [self.cors_origin]


@lru_cache
def get_settings() -> Settings:
    s = Settings()
    if s.secret_key == _DEFAULT_SECRET:
        warnings.warn(
            "Using default SECRET_KEY! Set SECRET_KEY in .env for production.",
            stacklevel=2,
        )
    return s
