"""Integration tests for Phase 1 world-schema migration and reconciliation evidence."""

from __future__ import annotations

import importlib.util
import json
import sqlite3
from pathlib import Path


def _load_migration_module():
    script_path = Path(__file__).resolve().parents[2] / "scripts" / "migrate_phase1_world_schema.py"
    spec = importlib.util.spec_from_file_location("migrate_phase1_world_schema", script_path)
    module = importlib.util.module_from_spec(spec)
    assert spec is not None and spec.loader is not None
    spec.loader.exec_module(module)
    return module


def _init_legacy_schema(db_path: Path, save_file: Path) -> None:
    conn = sqlite3.connect(db_path)
    try:
        conn.executescript(
            """
            CREATE TABLE tenants (
                id INTEGER PRIMARY KEY,
                name TEXT NOT NULL
            );

            CREATE TABLE users (
                id INTEGER PRIMARY KEY,
                tenant_id INTEGER,
                username TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                role TEXT,
                encrypted_api_key TEXT,
                default_provider TEXT,
                created_at TEXT
            );

            CREATE TABLE characters (
                id INTEGER PRIMARY KEY,
                tenant_id INTEGER,
                user_id INTEGER,
                name TEXT NOT NULL,
                avatar TEXT,
                personality TEXT,
                background TEXT,
                speech_style TEXT,
                sprites JSON,
                created_at TEXT
            );

            CREATE TABLE teacher_personas (
                id INTEGER PRIMARY KEY,
                tenant_id INTEGER,
                character_id INTEGER,
                name TEXT NOT NULL,
                version TEXT,
                traits JSON,
                system_prompt_template TEXT,
                is_active INTEGER,
                created_at TEXT,
                updated_at TEXT
            );

            CREATE TABLE subjects (
                id INTEGER PRIMARY KEY,
                tenant_id INTEGER,
                character_id INTEGER,
                name TEXT NOT NULL,
                description TEXT,
                target_level TEXT,
                scene_background TEXT,
                created_at TEXT
            );

            CREATE TABLE learner_profiles (
                id INTEGER PRIMARY KEY,
                tenant_id INTEGER,
                user_id INTEGER,
                subject_id INTEGER,
                learning_style JSON,
                cognitive_traits JSON,
                emotional_traits JSON,
                knowledge_graph JSON,
                created_at TEXT,
                updated_at TEXT
            );

            CREATE TABLE progress_trackings (
                id INTEGER PRIMARY KEY,
                tenant_id INTEGER,
                subject_id INTEGER,
                user_id INTEGER,
                topic TEXT,
                mastery_level INTEGER,
                last_review TEXT,
                next_review TEXT,
                fsrs_state JSON
            );

            CREATE TABLE sessions (
                id INTEGER PRIMARY KEY,
                tenant_id INTEGER,
                subject_id INTEGER,
                user_id INTEGER,
                started_at TEXT,
                ended_at TEXT,
                system_prompt TEXT,
                relationship_stage TEXT,
                teacher_persona_id INTEGER,
                learner_profile_id INTEGER
            );

            CREATE TABLE chat_messages (
                id INTEGER PRIMARY KEY,
                tenant_id INTEGER,
                session_id INTEGER,
                sender_type TEXT,
                sender_id INTEGER,
                content TEXT,
                timestamp TEXT,
                emotion_analysis JSON,
                used_memory_ids JSON
            );

            CREATE TABLE saves (
                id INTEGER PRIMARY KEY,
                tenant_id INTEGER,
                user_id INTEGER,
                subject_id INTEGER,
                session_id INTEGER,
                save_name TEXT,
                file_path TEXT,
                memory_ids JSON,
                created_at TEXT
            );
            """
        )

        conn.execute("INSERT INTO tenants(id, name) VALUES (1, 'default')")
        conn.execute(
            "INSERT INTO users(id, tenant_id, username, password_hash, role, created_at) VALUES (1, 1, 'u1', 'hash', 'student', datetime('now'))"
        )
        conn.execute(
            """
            INSERT INTO characters(id, tenant_id, user_id, name, background, sprites, created_at)
            VALUES (10, 1, 1, 'Socrates', 'philosopher', '{}', datetime('now'))
            """
        )
        conn.execute(
            """
            INSERT INTO characters(id, tenant_id, user_id, name, background, sprites, created_at)
            VALUES (11, 1, 1, 'Traveler', 'student self', '{}', datetime('now'))
            """
        )
        conn.execute(
            """
            INSERT INTO teacher_personas(id, tenant_id, character_id, name, version, traits, system_prompt_template, is_active, created_at, updated_at)
            VALUES (30, 1, 10, 'Default Persona', '1.0', '[]', 'prompt', 1, datetime('now'), datetime('now'))
            """
        )
        conn.execute(
            """
            INSERT INTO subjects(id, tenant_id, character_id, name, description, target_level, scene_background, created_at)
            VALUES (20, 1, 10, 'Logic', 'Intro logic', 'beginner', NULL, datetime('now'))
            """
        )
        conn.execute(
            """
            INSERT INTO learner_profiles(id, tenant_id, user_id, subject_id, learning_style, cognitive_traits, emotional_traits, knowledge_graph, created_at, updated_at)
            VALUES (60, 1, 1, 20, '{"visual": true}', '{"planning": "mid"}', '{"stress": "low"}', '{}', datetime('now'), datetime('now'))
            """
        )
        conn.execute(
            """
            INSERT INTO sessions(id, tenant_id, subject_id, user_id, started_at, ended_at, system_prompt, relationship_stage, teacher_persona_id, learner_profile_id)
            VALUES (40, 1, 20, 1, datetime('now'), NULL, 'sys', 'friend', 30, 60)
            """
        )
        conn.execute(
            """
            INSERT INTO chat_messages(id, tenant_id, session_id, sender_type, sender_id, content, timestamp)
            VALUES (1, 1, 40, 'user', 1, 'hello', datetime('now'))
            """
        )
        conn.execute(
            """
            INSERT INTO chat_messages(id, tenant_id, session_id, sender_type, sender_id, content, timestamp)
            VALUES (2, 1, 40, 'teacher', NULL, 'hi', datetime('now'))
            """
        )

        fsrs_json = json.dumps(
            {
                "difficulty": 3.2,
                "stability": 5.5,
                "reps": 2,
                "due": "2026-04-02T00:00:00+00:00",
                "last_review": "2026-04-01T00:00:00+00:00",
            }
        )
        conn.execute(
            """
            INSERT INTO progress_trackings(id, tenant_id, subject_id, user_id, topic, mastery_level, last_review, next_review, fsrs_state)
            VALUES (70, 1, 20, 1, 'recursion', 42, datetime('now'), datetime('now'), ?)
            """,
            (fsrs_json,),
        )

        save_payload = {
            "session_meta": {"relationship_stage": "friend", "teacher_persona_id": 30, "subject_id": 20},
            "chat_history": [],
            "progress": {},
            "learner_profile_snapshot": None,
            "memory_ids": [],
        }
        save_file.write_text(json.dumps(save_payload, ensure_ascii=False), encoding="utf-8")

        conn.execute(
            """
            INSERT INTO saves(id, tenant_id, user_id, subject_id, session_id, save_name, file_path, memory_ids, created_at)
            VALUES (50, 1, 1, 20, 40, 'save1', ?, '[]', datetime('now'))
            """,
            (str(save_file),),
        )

        conn.commit()
    finally:
        conn.close()


class TestPhase1Migration:
    def test_migration_reconciliation_and_backfill_evidence(self, tmp_path):
        module = _load_migration_module()

        db_path = tmp_path / "legacy.db"
        report_path = tmp_path / "migration_report.json"
        save_file = tmp_path / "legacy_save.json"

        _init_legacy_schema(db_path, save_file)

        report = module.migrate_phase1(str(db_path), str(report_path))

        assert report["status"] == "success"
        assert report["pre_reconciliation"]["row_counts"]["courses"] is None
        assert report["pre_reconciliation"]["row_counts"]["checkpoints"] is None
        assert report["post_reconciliation"]["row_counts"]["courses"] == 1
        assert report["post_reconciliation"]["row_counts"]["checkpoints"] == 1
        assert report["post_reconciliation"]["row_counts"]["knowledge"] == report["post_reconciliation"]["row_counts"]["worlds"]

        item14 = report["backfill_results"]["item_14_course_world_backfill"]
        assert item14["courses_total"] == 1
        assert item14["courses_with_world_id"] == 1
        assert item14["fill_rate"] == 1.0

        item15 = report["backfill_results"]["item_15_session_world_sage_backfill"]
        assert item15["migrated_rows"] == 1
        assert item15["filled_world_id"] == 1
        assert item15["filled_sage_character_id"] == 1

        item16 = report["backfill_results"]["item_16_saves_to_checkpoints"]
        assert item16["legacy_saves"] == 1
        assert item16["migrated_checkpoints"] == 1
        assert item16["fill_rate_world_id"] == 1.0
        assert report["backfill_results"]["item_11_tenant_cleanup"]["dropped_tables"] == ["tenants"]

        assert Path(report["backup_path"]).exists()
        assert report_path.exists()

        conn = sqlite3.connect(db_path)
        try:
            cur = conn.cursor()
            # saves table should be removed after migration
            saves_exists = cur.execute(
                "SELECT COUNT(*) FROM sqlite_master WHERE type='table' AND name='saves'"
            ).fetchone()[0]
            assert saves_exists == 0

            subjects_exists = cur.execute(
                "SELECT COUNT(*) FROM sqlite_master WHERE type='table' AND name='subjects'"
            ).fetchone()[0]
            assert subjects_exists == 0

            tenants_exists = cur.execute(
                "SELECT COUNT(*) FROM sqlite_master WHERE type='table' AND name='tenants'"
            ).fetchone()[0]
            assert tenants_exists == 0

            for table in [
                "users",
                "characters",
                "teacher_personas",
                "courses",
                "learner_profiles",
                "progress_trackings",
                "sessions",
                "chat_messages",
                "checkpoints",
            ]:
                columns = [row[1] for row in cur.execute(f"PRAGMA table_info({table})").fetchall()]
                assert "tenant_id" not in columns

            # relationship should be JSON and preserve stage semantics
            relationship_raw = cur.execute("SELECT relationship FROM sessions WHERE id = 40").fetchone()[0]
            relationship = json.loads(relationship_raw)
            assert relationship["stage"] == "friend"

            fsrs_count = cur.execute("SELECT COUNT(*) FROM fsrs_states WHERE concept_id = 'recursion'").fetchone()[0]
            assert fsrs_count == 1
        finally:
            conn.close()

    def test_migration_falls_back_when_drop_column_unsupported(self, tmp_path, monkeypatch):
        module = _load_migration_module()

        db_path = tmp_path / "legacy_no_drop.db"
        report_path = tmp_path / "migration_report_no_drop.json"
        save_file = tmp_path / "legacy_save_no_drop.json"

        _init_legacy_schema(db_path, save_file)
        monkeypatch.setattr(module, "_sqlite_supports_drop_column", lambda _conn: False)

        report = module.migrate_phase1(str(db_path), str(report_path))
        assert report["status"] == "success"
        cleanup = report["backfill_results"]["item_11_tenant_cleanup"]
        assert cleanup["tenant_cleanup_fallback_tables"] != []
        assert "users" in cleanup["dropped_tenant_columns"]
        assert report["post_reconciliation"]["anomaly_samples"]["tenant_columns_present"] == []

    def test_migration_reentry_is_idempotent(self, tmp_path):
        module = _load_migration_module()

        db_path = tmp_path / "legacy_reentry.db"
        report_path_first = tmp_path / "migration_report_first.json"
        report_path_second = tmp_path / "migration_report_second.json"
        save_file = tmp_path / "legacy_save_reentry.json"

        _init_legacy_schema(db_path, save_file)

        first = module.migrate_phase1(str(db_path), str(report_path_first))
        second = module.migrate_phase1(str(db_path), str(report_path_second))

        assert first["status"] == "success"
        assert second["status"] == "success"
        assert second["post_reconciliation"]["anomaly_samples"]["legacy_tables_present"] == []
        assert second["post_reconciliation"]["anomaly_samples"]["tenant_columns_present"] == []
