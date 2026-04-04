from __future__ import annotations

import json
import sqlite3
from pathlib import Path

from migrate_phase1_world_schema import migrate_phase1


def init_legacy_db(db_path: Path, save_file: Path) -> None:
    if db_path.exists():
        db_path.unlink()

    conn = sqlite3.connect(db_path)
    try:
        conn.executescript(
            """
            CREATE TABLE users (
                id INTEGER PRIMARY KEY,
                username TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                role TEXT,
                encrypted_api_key TEXT,
                default_provider TEXT,
                created_at TEXT
            );

            CREATE TABLE characters (
                id INTEGER PRIMARY KEY,
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
                character_id INTEGER,
                name TEXT NOT NULL,
                description TEXT,
                target_level TEXT,
                scene_background TEXT,
                created_at TEXT
            );

            CREATE TABLE learner_profiles (
                id INTEGER PRIMARY KEY,
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

        conn.execute(
            "INSERT INTO users(id, username, password_hash, role, created_at) VALUES (1, 'alice', 'hash', 'student', datetime('now'))"
        )
        conn.execute(
            "INSERT INTO characters(id, user_id, name, background, sprites, created_at) VALUES (10, 1, 'Socrates', 'philosopher', '{}', datetime('now'))"
        )
        conn.execute(
            "INSERT INTO characters(id, user_id, name, background, sprites, created_at) VALUES (11, 1, 'Alice', 'traveler', '{}', datetime('now'))"
        )
        conn.execute(
            """
            INSERT INTO teacher_personas(id, character_id, name, version, traits, system_prompt_template, is_active, created_at, updated_at)
            VALUES (30, 10, 'Default Persona', '1.0', '[]', 'prompt', 1, datetime('now'), datetime('now'))
            """
        )
        conn.execute(
            "INSERT INTO subjects(id, character_id, name, description, target_level, scene_background, created_at) VALUES (20, 10, 'Logic', 'Intro', 'beginner', NULL, datetime('now'))"
        )
        conn.execute(
            """
            INSERT INTO learner_profiles(id, user_id, subject_id, learning_style, cognitive_traits, emotional_traits, knowledge_graph, created_at, updated_at)
            VALUES (60, 1, 20, '{\"visual\": true}', '{\"planning\": \"mid\"}', '{\"stress\": \"low\"}', '{}', datetime('now'), datetime('now'))
            """
        )
        conn.execute(
            "INSERT INTO sessions(id, subject_id, user_id, started_at, ended_at, system_prompt, relationship_stage, teacher_persona_id, learner_profile_id) VALUES (40, 20, 1, datetime('now'), NULL, 'sys', 'friend', 30, 60)"
        )
        conn.execute(
            "INSERT INTO chat_messages(id, session_id, sender_type, sender_id, content, timestamp) VALUES (1, 40, 'user', 1, 'hello', datetime('now'))"
        )
        conn.execute(
            "INSERT INTO chat_messages(id, session_id, sender_type, sender_id, content, timestamp) VALUES (2, 40, 'teacher', NULL, 'hi', datetime('now'))"
        )

        fsrs = {
            "difficulty": 3.2,
            "stability": 5.1,
            "reps": 2,
            "due": "2026-04-02T00:00:00+00:00",
            "last_review": "2026-04-01T00:00:00+00:00",
        }
        conn.execute(
            "INSERT INTO progress_trackings(id, subject_id, user_id, topic, mastery_level, last_review, next_review, fsrs_state) VALUES (70, 20, 1, 'recursion', 40, datetime('now'), datetime('now'), ?)",
            (json.dumps(fsrs),),
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
            "INSERT INTO saves(id, user_id, subject_id, session_id, save_name, file_path, memory_ids, created_at) VALUES (50, 1, 20, 40, 'save1', ?, '[]', datetime('now'))",
            (str(save_file),),
        )

        conn.commit()
    finally:
        conn.close()


def main() -> None:
    out_dir = Path("backend") / "migration_evidence"
    out_dir.mkdir(parents=True, exist_ok=True)

    db_path = out_dir / "phase1_legacy_sample.db"
    report_path = out_dir / "phase1_reconciliation_report.json"
    save_file = out_dir / "legacy_save.json"

    init_legacy_db(db_path, save_file)

    report = migrate_phase1(str(db_path), str(report_path))

    summary = {
        "status": report["status"],
        "backup_path": report["backup_path"],
        "post_row_counts": report["post_reconciliation"]["row_counts"],
        "backfill_results": report["backfill_results"],
        "null_stats": report["post_reconciliation"]["null_stats"],
        "anomaly_samples": report["post_reconciliation"]["anomaly_samples"],
        "report_path": str(report_path),
    }

    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
