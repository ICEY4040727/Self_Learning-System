"""Risk 3 stress tests — multithread gateway writes + PostgreSQL DB triggers.

Run only in nightly / manual stress pipelines:

    USER_LLM_STRESS=1 DATABASE_URL=postgresql://... pytest tests/user_llm/test_risk3_stress.py -v
"""
from __future__ import annotations

import os
import threading

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.exc import DBAPIError, IntegrityError
from sqlalchemy.orm import sessionmaker

from backend.models.models import User
from backend.services.user_llm_db_audit import audit_user_llm_consistency
from backend.services.user_llm_settings import lock_user_for_update, update_provider_settings

from .conftest import create_user

pytestmark = pytest.mark.user_llm_stress


def _require_stress_env() -> str:
    if os.environ.get("USER_LLM_STRESS") != "1":
        pytest.skip("Set USER_LLM_STRESS=1 to run stress tests")
    url = os.environ.get("DATABASE_URL", "")
    if not url.startswith("postgresql"):
        pytest.skip("PostgreSQL DATABASE_URL required for stress tests")
    return url


@pytest.fixture(scope="module")
def pg_engine():
    url = _require_stress_env()
    engine = create_engine(url, pool_pre_ping=True)
    yield engine
    engine.dispose()


@pytest.fixture(autouse=True)
def isolate_pg_users(pg_engine):
    """Stress tests share one PostgreSQL database; reset users between cases."""
    with pg_engine.begin() as conn:
        conn.execute(text("TRUNCATE TABLE users RESTART IDENTITY"))
    yield


@pytest.fixture
def pg_session_factory(pg_engine):
    return sessionmaker(autocommit=False, autoflush=False, bind=pg_engine)


class TestPostgresDbTriggers:
    def test_raw_sql_legacy_only_update_is_rejected(self, pg_session_factory):
        session = pg_session_factory()
        user = create_user(session, username="pg-legacy-only")
        user_id = user.id
        session.close()

        session = pg_session_factory()
        with pytest.raises((IntegrityError, DBAPIError), match="legacy LLM columns cannot be updated alone"):
            session.execute(
                text("UPDATE users SET model = :model WHERE id = :id"),
                {"model": "bad-model", "id": user_id},
            )
        session.rollback()
        session.close()

    def test_json_sql_update_syncs_legacy_mirror(self, pg_session_factory):
        session = pg_session_factory()
        user = create_user(session, username="pg-json-sync")
        user.default_provider = "openai"
        user.model = "legacy-model"
        user.llm_provider_settings = {"openai": {"model": "legacy-model"}}
        session.commit()
        user_id = user.id
        session.close()

        session = pg_session_factory()
        session.execute(
            text("UPDATE users SET llm_provider_settings = :settings WHERE id = :id"),
            {
                "settings": '{"openai": {"model": "json-sync-model", "base_url": "https://api.openai.example/v1"}}',
                "id": user_id,
            },
        )
        session.commit()
        refreshed = session.get(User, user_id)
        assert refreshed is not None
        assert refreshed.model == "json-sync-model"
        assert refreshed.llm_base_url == "https://api.openai.example/v1"
        assert audit_user_llm_consistency(session) == []
        session.close()


class TestMultithreadedGatewayWrites:
    def test_multithreaded_gateway_updates_stay_consistent(self, pg_session_factory):
        session = pg_session_factory()
        user = create_user(session, username="pg-concurrent")
        user_id = user.id
        session.close()

        thread_count = 10
        errors: list[Exception] = []
        barrier = threading.Barrier(thread_count)

        def worker(index: int) -> None:
            worker_session = pg_session_factory()
            try:
                barrier.wait(timeout=10)
                locked = lock_user_for_update(worker_session, user_id)
                update_provider_settings(
                    locked,
                    "openai",
                    model=f"gpt-thread-{index}",
                    base_url="https://api.openai.example/v1",
                )
                worker_session.commit()
            except Exception as exc:
                errors.append(exc)
            finally:
                worker_session.close()

        threads = [threading.Thread(target=worker, args=(i,)) for i in range(thread_count)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join(timeout=30)

        assert not errors, errors

        verify = pg_session_factory()
        final = verify.get(User, user_id)
        assert final is not None
        assert final.model.startswith("gpt-thread-")
        assert final.llm_provider_settings["openai"]["model"] == final.model
        assert audit_user_llm_consistency(verify) == []
        verify.close()
