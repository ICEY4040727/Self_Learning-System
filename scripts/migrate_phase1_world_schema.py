from __future__ import annotations

import argparse
import json
import os
import shutil
import sqlite3
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


def _utc_iso() -> str:
    return datetime.now(UTC).isoformat()


def _connect(db_path: str) -> sqlite3.Connection:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn


def _table_exists(conn: sqlite3.Connection, table: str) -> bool:
    row = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name=?",
        (table,),
    ).fetchone()
    return row is not None


def _column_exists(conn: sqlite3.Connection, table: str, column: str) -> bool:
    if not _table_exists(conn, table):
        return False
    cols = conn.execute(f"PRAGMA table_info({table})").fetchall()
    return any(c[1] == column for c in cols)


def _fetch_rows(conn: sqlite3.Connection, sql: str, params: tuple = ()) -> list[dict[str, Any]]:
    rows = conn.execute(sql, params).fetchall()
    return [dict(r) for r in rows]


def _row_count(conn: sqlite3.Connection, table: str) -> int | None:
    if not _table_exists(conn, table):
        return None
    return int(conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0])


def _null_count(conn: sqlite3.Connection, table: str, column: str) -> dict[str, int] | None:
    if not _table_exists(conn, table) or not _column_exists(conn, table, column):
        return None
    total = int(conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0])
    nulls = int(conn.execute(f"SELECT COUNT(*) FROM {table} WHERE {column} IS NULL").fetchone()[0])
    return {"total": total, "null": nulls, "filled": total - nulls}


def _ensure_characters_type(conn: sqlite3.Connection) -> None:
    if not _column_exists(conn, "characters", "type"):
        conn.execute("ALTER TABLE characters ADD COLUMN type TEXT DEFAULT 'sage'")


def _create_world_tables(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS worlds (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL REFERENCES users(id),
            name TEXT NOT NULL,
            description TEXT,
            scenes JSON DEFAULT '{}',
            created_at TEXT DEFAULT (datetime('now'))
        )
        """
    )

    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS world_characters (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            world_id INTEGER NOT NULL REFERENCES worlds(id) ON DELETE CASCADE,
            character_id INTEGER NOT NULL REFERENCES characters(id) ON DELETE CASCADE,
            role TEXT NOT NULL,
            is_primary INTEGER DEFAULT 0,
            UNIQUE(world_id, character_id)
        )
        """
    )

    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS knowledge (
            world_id INTEGER PRIMARY KEY REFERENCES worlds(id) ON DELETE CASCADE,
            graph JSON NOT NULL DEFAULT '{}'
        )
        """
    )

    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS checkpoints (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL REFERENCES users(id),
            world_id INTEGER NOT NULL REFERENCES worlds(id),
            session_id INTEGER REFERENCES sessions(id),
            save_name TEXT NOT NULL,
            message_index INTEGER NOT NULL DEFAULT 0,
            state JSON NOT NULL,
            thumbnail_path TEXT,
            created_at TEXT DEFAULT (datetime('now'))
        )
        """
    )

    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS fsrs_states (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            world_id INTEGER NOT NULL REFERENCES worlds(id) ON DELETE CASCADE,
            concept_id TEXT NOT NULL,
            difficulty REAL,
            stability REAL,
            last_review TEXT,
            next_review TEXT,
            reps INTEGER DEFAULT 0,
            UNIQUE(world_id, concept_id)
        )
        """
    )


def _derive_relationship(stage: str | None) -> dict[str, Any]:
    stage = (stage or "stranger").strip() or "stranger"
    defaults = {
        "stranger": (0.05, 0.05, 0.05, 0.05),
        "acquaintance": (0.25, 0.25, 0.25, 0.25),
        "friend": (0.45, 0.45, 0.45, 0.45),
        "mentor": (0.65, 0.65, 0.65, 0.65),
        "partner": (0.85, 0.85, 0.85, 0.85),
    }
    trust, familiarity, respect, comfort = defaults.get(stage, defaults["stranger"])
    return {
        "dimensions": {
            "trust": trust,
            "familiarity": familiarity,
            "respect": respect,
            "comfort": comfort,
        },
        "stage": stage,
        "history": [],
    }


def _stage_from_relationship(relationship_value: Any) -> str:
    if isinstance(relationship_value, str):
        try:
            data = json.loads(relationship_value)
            if isinstance(data, dict) and isinstance(data.get("stage"), str):
                return data["stage"]
        except json.JSONDecodeError:
            pass
    if isinstance(relationship_value, dict):
        stage = relationship_value.get("stage")
        if isinstance(stage, str):
            return stage
    return "stranger"


def _create_worlds_for_characters(conn: sqlite3.Connection) -> dict[str, Any]:
    characters = _fetch_rows(
        conn,
        "SELECT id, user_id, name, background, COALESCE(type, 'sage') AS type FROM characters",
    )

    char_world_map: dict[int, int] = {}
    created_worlds = 0
    created_links = 0

    existing_links = _fetch_rows(conn, "SELECT world_id, character_id FROM world_characters")
    for row in existing_links:
        char_world_map[int(row["character_id"])] = int(row["world_id"])

    for ch in characters:
        cid = int(ch["id"])
        if cid in char_world_map:
            continue

        world_name = f"{ch['name']} World"
        conn.execute(
            """
            INSERT INTO worlds (user_id, name, description, scenes, created_at)
            VALUES (?, ?, ?, '{}', datetime('now'))
            """,
            (ch["user_id"], world_name, ch.get("background")),
        )
        wid = int(conn.execute("SELECT last_insert_rowid()").fetchone()[0])
        created_worlds += 1

        role = ch.get("type") or "sage"
        conn.execute(
            """
            INSERT OR IGNORE INTO world_characters (world_id, character_id, role, is_primary)
            VALUES (?, ?, ?, 1)
            """,
            (wid, cid, role),
        )
        created_links += 1

        char_world_map[cid] = wid

    # Ensure every world has one knowledge row with empty JSON.
    conn.execute(
        """
        INSERT OR IGNORE INTO knowledge(world_id, graph)
        SELECT id, '{}' FROM worlds
        """
    )

    return {
        "created_worlds": created_worlds,
        "created_world_characters": created_links,
        "character_to_world_count": len(char_world_map),
        "char_world_map": char_world_map,
    }


def _rebuild_courses(conn: sqlite3.Connection, char_world_map: dict[int, int]) -> dict[str, Any]:
    course_character_map: dict[int, int] = {}

    legacy_rows: list[dict[str, Any]] = []
    if _table_exists(conn, "subjects"):
        legacy_rows = _fetch_rows(
            conn,
            "SELECT id, character_id, name, description, target_level, created_at FROM subjects",
        )
        conn.execute("DROP TABLE subjects")
    elif _table_exists(conn, "courses") and _column_exists(conn, "courses", "character_id"):
        legacy_rows = _fetch_rows(
            conn,
            "SELECT id, character_id, name, description, target_level, created_at FROM courses",
        )
        conn.execute("DROP TABLE courses")

    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS courses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            world_id INTEGER NOT NULL REFERENCES worlds(id) ON DELETE CASCADE,
            name TEXT NOT NULL,
            description TEXT,
            target_level TEXT,
            created_at TEXT DEFAULT (datetime('now'))
        )
        """
    )

    inserted = 0
    anomalies: list[dict[str, Any]] = []

    if legacy_rows:
        for row in legacy_rows:
            cid = row.get("character_id")
            world_id = char_world_map.get(int(cid)) if cid is not None else None
            if world_id is None:
                anomalies.append({"course_id": row["id"], "character_id": cid, "reason": "missing_world"})
                continue

            conn.execute(
                """
                INSERT OR REPLACE INTO courses(id, world_id, name, description, target_level, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    row["id"],
                    world_id,
                    row["name"],
                    row.get("description"),
                    row.get("target_level"),
                    row.get("created_at") or datetime.now(UTC).isoformat(),
                ),
            )
            inserted += 1
            course_character_map[int(row["id"])] = int(cid)
    else:
        # Already migrated schema; keep existing course rows.
        rows = _fetch_rows(conn, "SELECT id, world_id FROM courses")
        inserted = len(rows)

    return {
        "inserted_courses": inserted,
        "course_character_map": course_character_map,
        "anomaly_samples": anomalies[:10],
    }


def _rebuild_lesson_plans(conn: sqlite3.Connection) -> None:
    if not _table_exists(conn, "lesson_plans"):
        return

    if _column_exists(conn, "lesson_plans", "course_id") and not _column_exists(conn, "lesson_plans", "subject_id"):
        return

    rows = _fetch_rows(conn, "SELECT id, subject_id, content, created_at FROM lesson_plans")
    conn.execute("DROP TABLE lesson_plans")
    conn.execute(
        """
        CREATE TABLE lesson_plans (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            course_id INTEGER NOT NULL REFERENCES courses(id),
            content TEXT NOT NULL,
            created_at TEXT DEFAULT (datetime('now'))
        )
        """
    )
    for row in rows:
        conn.execute(
            "INSERT INTO lesson_plans(id, course_id, content, created_at) VALUES (?, ?, ?, ?)",
            (row["id"], row["subject_id"], row["content"], row.get("created_at")),
        )


def _rebuild_learning_diaries(conn: sqlite3.Connection) -> None:
    if not _table_exists(conn, "learning_diaries"):
        return

    if _column_exists(conn, "learning_diaries", "course_id") and not _column_exists(conn, "learning_diaries", "subject_id"):
        return

    rows = _fetch_rows(conn, "SELECT id, subject_id, user_id, date, content, reflection FROM learning_diaries")
    conn.execute("DROP TABLE learning_diaries")
    conn.execute(
        """
        CREATE TABLE learning_diaries (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            course_id INTEGER NOT NULL REFERENCES courses(id),
            user_id INTEGER NOT NULL REFERENCES users(id),
            date TEXT NOT NULL,
            content TEXT NOT NULL,
            reflection TEXT
        )
        """
    )
    for row in rows:
        conn.execute(
            """
            INSERT INTO learning_diaries(id, course_id, user_id, date, content, reflection)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (row["id"], row["subject_id"], row["user_id"], row["date"], row["content"], row.get("reflection")),
        )


def _rebuild_progress_and_fsrs(conn: sqlite3.Connection, course_world_map: dict[int, int]) -> dict[str, Any]:
    if not _table_exists(conn, "progress_trackings"):
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS progress_trackings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                course_id INTEGER NOT NULL REFERENCES courses(id),
                user_id INTEGER NOT NULL REFERENCES users(id),
                topic TEXT NOT NULL,
                mastery_level INTEGER DEFAULT 0,
                last_review TEXT,
                next_review TEXT
            )
            """
        )
        return {
            "migrated_rows": 0,
            "fsrs_rows": 0,
            "fsrs_anomaly_samples": [],
        }

    has_subject = _column_exists(conn, "progress_trackings", "subject_id")
    has_course = _column_exists(conn, "progress_trackings", "course_id")
    has_fsrs_json = _column_exists(conn, "progress_trackings", "fsrs_state")

    if has_subject:
        rows = _fetch_rows(
            conn,
            "SELECT id, subject_id, user_id, topic, mastery_level, last_review, next_review, fsrs_state FROM progress_trackings",
        )
    elif has_course:
        select_cols = "id, course_id, user_id, topic, mastery_level, last_review, next_review"
        if has_fsrs_json:
            select_cols += ", fsrs_state"
        else:
            select_cols += ", NULL AS fsrs_state"
        rows = _fetch_rows(conn, f"SELECT {select_cols} FROM progress_trackings")
    else:
        rows = []

    conn.execute("DROP TABLE progress_trackings")
    conn.execute(
        """
        CREATE TABLE progress_trackings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            course_id INTEGER NOT NULL REFERENCES courses(id),
            user_id INTEGER NOT NULL REFERENCES users(id),
            topic TEXT NOT NULL,
            mastery_level INTEGER DEFAULT 0,
            last_review TEXT,
            next_review TEXT
        )
        """
    )

    migrated_rows = 0
    fsrs_rows = 0
    fsrs_anomalies: list[dict[str, Any]] = []

    for row in rows:
        course_id = row.get("subject_id") if has_subject else row.get("course_id")
        if course_id is None:
            fsrs_anomalies.append({"progress_id": row["id"], "reason": "missing_course_id"})
            continue

        conn.execute(
            """
            INSERT INTO progress_trackings(id, course_id, user_id, topic, mastery_level, last_review, next_review)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                row["id"],
                course_id,
                row["user_id"],
                row["topic"],
                row.get("mastery_level") or 0,
                row.get("last_review"),
                row.get("next_review"),
            ),
        )
        migrated_rows += 1

        fsrs_raw = row.get("fsrs_state")
        if not fsrs_raw:
            continue

        world_id = course_world_map.get(int(course_id))
        if world_id is None:
            fsrs_anomalies.append({"progress_id": row["id"], "reason": "missing_world_for_course"})
            continue

        try:
            fsrs_data = fsrs_raw if isinstance(fsrs_raw, dict) else json.loads(fsrs_raw)
        except (json.JSONDecodeError, TypeError):
            fsrs_anomalies.append({"progress_id": row["id"], "reason": "invalid_fsrs_json"})
            continue

        concept_id = (row.get("topic") or f"progress-{row['id']}").strip() or f"progress-{row['id']}"

        conn.execute(
            """
            INSERT INTO fsrs_states(world_id, concept_id, difficulty, stability, last_review, next_review, reps)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(world_id, concept_id)
            DO UPDATE SET
                difficulty = excluded.difficulty,
                stability = excluded.stability,
                last_review = excluded.last_review,
                next_review = excluded.next_review,
                reps = excluded.reps
            """,
            (
                world_id,
                concept_id,
                fsrs_data.get("difficulty"),
                fsrs_data.get("stability"),
                fsrs_data.get("last_review"),
                fsrs_data.get("due") or fsrs_data.get("next_review"),
                fsrs_data.get("reps") or 0,
            ),
        )
        fsrs_rows += 1

    return {
        "migrated_rows": migrated_rows,
        "fsrs_rows": fsrs_rows,
        "fsrs_anomaly_samples": fsrs_anomalies[:10],
    }


def _rebuild_learner_profiles(conn: sqlite3.Connection, course_world_map: dict[int, int]) -> dict[str, Any]:
    if not _table_exists(conn, "learner_profiles"):
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS learner_profiles (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL REFERENCES users(id),
                world_id INTEGER NOT NULL REFERENCES worlds(id),
                profile JSON DEFAULT '{}',
                created_at TEXT DEFAULT (datetime('now')),
                updated_at TEXT DEFAULT (datetime('now'))
            )
            """
        )
        return {"migrated_rows": 0, "fill_rate_world_id": 1.0, "anomaly_samples": []}

    if _column_exists(conn, "learner_profiles", "profile") and _column_exists(conn, "learner_profiles", "world_id"):
        total = _row_count(conn, "learner_profiles") or 0
        filled = total - (_null_count(conn, "learner_profiles", "world_id") or {"null": 0})["null"]
        return {
            "migrated_rows": total,
            "fill_rate_world_id": round((filled / total), 4) if total else 1.0,
            "anomaly_samples": [],
        }

    rows = _fetch_rows(
        conn,
        """
        SELECT
            id,
            user_id,
            subject_id,
            learning_style,
            cognitive_traits,
            emotional_traits,
            created_at,
            updated_at
        FROM learner_profiles
        """,
    )

    conn.execute("DROP TABLE learner_profiles")
    conn.execute(
        """
        CREATE TABLE learner_profiles (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL REFERENCES users(id),
            world_id INTEGER NOT NULL REFERENCES worlds(id),
            profile JSON DEFAULT '{}',
            created_at TEXT DEFAULT (datetime('now')),
            updated_at TEXT DEFAULT (datetime('now'))
        )
        """
    )

    migrated = 0
    anomalies: list[dict[str, Any]] = []

    for row in rows:
        world_id = course_world_map.get(int(row["subject_id"])) if row.get("subject_id") else None
        if world_id is None:
            anomalies.append({"profile_id": row["id"], "reason": "missing_world"})
            continue

        def parse_json(value: Any) -> dict[str, Any]:
            if isinstance(value, dict):
                return value
            if value is None:
                return {}
            try:
                parsed = json.loads(value)
                return parsed if isinstance(parsed, dict) else {}
            except (json.JSONDecodeError, TypeError):
                return {}

        profile_json = {
            "preferences": parse_json(row.get("learning_style")),
            "affect": parse_json(row.get("emotional_traits")),
            "metacognition": parse_json(row.get("cognitive_traits")),
        }

        conn.execute(
            """
            INSERT INTO learner_profiles(id, user_id, world_id, profile, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                row["id"],
                row["user_id"],
                world_id,
                json.dumps(profile_json, ensure_ascii=False),
                row.get("created_at") or datetime.now(UTC).isoformat(),
                row.get("updated_at") or datetime.now(UTC).isoformat(),
            ),
        )
        migrated += 1

    return {
        "migrated_rows": migrated,
        "fill_rate_world_id": round((migrated / len(rows)), 4) if rows else 1.0,
        "anomaly_samples": anomalies[:10],
    }


def _select_primary_character(conn: sqlite3.Connection, world_id: int, role: str) -> int | None:
    row = conn.execute(
        """
        SELECT character_id
        FROM world_characters
        WHERE world_id = ? AND role = ?
        ORDER BY is_primary DESC, id ASC
        LIMIT 1
        """,
        (world_id, role),
    ).fetchone()
    return int(row[0]) if row else None


def _rebuild_sessions(conn: sqlite3.Connection, course_world_map: dict[int, int]) -> dict[str, Any]:
    if not _table_exists(conn, "sessions"):
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                course_id INTEGER NOT NULL REFERENCES courses(id),
                user_id INTEGER NOT NULL REFERENCES users(id),
                world_id INTEGER NOT NULL REFERENCES worlds(id),
                sage_character_id INTEGER REFERENCES characters(id),
                traveler_character_id INTEGER REFERENCES characters(id),
                started_at TEXT DEFAULT (datetime('now')),
                ended_at TEXT,
                system_prompt TEXT,
                relationship JSON DEFAULT '{"dimensions": {"trust": 0.0, "familiarity": 0.0, "respect": 0.0, "comfort": 0.0}, "stage": "stranger", "history": []}',
                teacher_persona_id INTEGER REFERENCES teacher_personas(id),
                learner_profile_id INTEGER REFERENCES learner_profiles(id),
                parent_checkpoint_id INTEGER REFERENCES checkpoints(id),
                branch_name TEXT
            )
            """
        )
        return {
            "migrated_rows": 0,
            "filled_world_id": 0,
            "filled_sage_character_id": 0,
            "filled_traveler_character_id": 0,
            "anomaly_samples": [],
        }

    if _column_exists(conn, "sessions", "course_id") and _column_exists(conn, "sessions", "relationship"):
        rows = _fetch_rows(conn, "SELECT id, course_id, world_id, sage_character_id, traveler_character_id FROM sessions")
        total = len(rows)
        return {
            "migrated_rows": total,
            "filled_world_id": sum(1 for r in rows if r.get("world_id") is not None),
            "filled_sage_character_id": sum(1 for r in rows if r.get("sage_character_id") is not None),
            "filled_traveler_character_id": sum(1 for r in rows if r.get("traveler_character_id") is not None),
            "anomaly_samples": [],
        }

    rows = _fetch_rows(
        conn,
        """
        SELECT
            id,
            subject_id,
            user_id,
            started_at,
            ended_at,
            system_prompt,
            relationship_stage,
            teacher_persona_id,
            learner_profile_id
        FROM sessions
        """,
    )

    conn.execute("DROP TABLE sessions")
    conn.execute(
        """
        CREATE TABLE sessions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            course_id INTEGER NOT NULL REFERENCES courses(id),
            user_id INTEGER NOT NULL REFERENCES users(id),
            world_id INTEGER NOT NULL REFERENCES worlds(id),
            sage_character_id INTEGER REFERENCES characters(id),
            traveler_character_id INTEGER REFERENCES characters(id),
            started_at TEXT DEFAULT (datetime('now')),
            ended_at TEXT,
            system_prompt TEXT,
            relationship JSON DEFAULT '{"dimensions": {"trust": 0.0, "familiarity": 0.0, "respect": 0.0, "comfort": 0.0}, "stage": "stranger", "history": []}',
            teacher_persona_id INTEGER REFERENCES teacher_personas(id),
            learner_profile_id INTEGER REFERENCES learner_profiles(id),
            parent_checkpoint_id INTEGER REFERENCES checkpoints(id),
            branch_name TEXT
        )
        """
    )

    migrated = 0
    filled_world = 0
    filled_sage = 0
    filled_traveler = 0
    anomalies: list[dict[str, Any]] = []

    for row in rows:
        course_id = row.get("subject_id")
        world_id = course_world_map.get(int(course_id)) if course_id is not None else None
        if world_id is None:
            anomalies.append({"session_id": row["id"], "reason": "missing_world"})
            continue

        sage_character_id = None
        if row.get("teacher_persona_id") is not None:
            tp = conn.execute(
                "SELECT character_id FROM teacher_personas WHERE id = ?",
                (row["teacher_persona_id"],),
            ).fetchone()
            if tp:
                sage_character_id = int(tp[0])

        if sage_character_id is None:
            sage_character_id = _select_primary_character(conn, world_id, "sage")

        traveler_character_id = _select_primary_character(conn, world_id, "traveler")

        relationship_json = _derive_relationship(row.get("relationship_stage"))

        conn.execute(
            """
            INSERT INTO sessions(
                id, course_id, user_id, world_id, sage_character_id, traveler_character_id,
                started_at, ended_at, system_prompt, relationship, teacher_persona_id,
                learner_profile_id, parent_checkpoint_id, branch_name
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, NULL, NULL)
            """,
            (
                row["id"],
                course_id,
                row["user_id"],
                world_id,
                sage_character_id,
                traveler_character_id,
                row.get("started_at") or datetime.now(UTC).isoformat(),
                row.get("ended_at"),
                row.get("system_prompt"),
                json.dumps(relationship_json, ensure_ascii=False),
                row.get("teacher_persona_id"),
                row.get("learner_profile_id"),
            ),
        )
        migrated += 1
        filled_world += 1
        if sage_character_id is not None:
            filled_sage += 1
        if traveler_character_id is not None:
            filled_traveler += 1

    return {
        "migrated_rows": migrated,
        "filled_world_id": filled_world,
        "filled_sage_character_id": filled_sage,
        "filled_traveler_character_id": filled_traveler,
        "anomaly_samples": anomalies[:10],
    }


def _migrate_saves_to_checkpoints(conn: sqlite3.Connection, course_world_map: dict[int, int]) -> dict[str, Any]:
    if not _table_exists(conn, "saves"):
        return {
            "legacy_saves": 0,
            "migrated_checkpoints": 0,
            "fill_rate_world_id": 1.0,
            "anomaly_samples": [],
        }

    rows = _fetch_rows(
        conn,
        """
        SELECT id, user_id, subject_id, session_id, save_name, file_path, memory_ids, created_at
        FROM saves
        ORDER BY id
        """,
    )

    migrated = 0
    anomalies: list[dict[str, Any]] = []

    for row in rows:
        world_id = course_world_map.get(int(row["subject_id"])) if row.get("subject_id") is not None else None
        if world_id is None:
            anomalies.append({"save_id": row["id"], "reason": "missing_world"})
            continue

        message_index = 0
        relationship_state: dict[str, Any] = _derive_relationship("stranger")

        session_id = row.get("session_id")
        if session_id is not None:
            message_index = int(
                conn.execute(
                    "SELECT COUNT(*) FROM chat_messages WHERE session_id = ?",
                    (session_id,),
                ).fetchone()[0]
            )
            srow = conn.execute(
                "SELECT relationship FROM sessions WHERE id = ?",
                (session_id,),
            ).fetchone()
            if srow and srow[0]:
                try:
                    parsed = json.loads(srow[0])
                    if isinstance(parsed, dict):
                        relationship_state = parsed
                except json.JSONDecodeError:
                    relationship_state = _derive_relationship("stranger")

        state_payload: dict[str, Any] = {
            "relationship": relationship_state,
            "legacy_save_id": row["id"],
            "legacy_file_path": row.get("file_path"),
            "memory_ids": row.get("memory_ids") if row.get("memory_ids") is not None else [],
        }

        file_path = row.get("file_path")
        if file_path and os.path.exists(file_path):
            try:
                with open(file_path, encoding="utf-8") as fh:
                    legacy = json.load(fh)
                if isinstance(legacy, dict):
                    state_payload["legacy_payload"] = legacy
            except (OSError, json.JSONDecodeError):
                anomalies.append({"save_id": row["id"], "reason": "invalid_save_file", "file_path": file_path})
        elif file_path:
            anomalies.append({"save_id": row["id"], "reason": "missing_save_file", "file_path": file_path})

        conn.execute(
            """
            INSERT INTO checkpoints(
                user_id, world_id, session_id, save_name, message_index, state, thumbnail_path, created_at
            )
            VALUES (?, ?, ?, ?, ?, ?, NULL, ?)
            """,
            (
                row["user_id"],
                world_id,
                session_id,
                row["save_name"],
                message_index,
                json.dumps(state_payload, ensure_ascii=False),
                row.get("created_at") or datetime.now(UTC).isoformat(),
            ),
        )
        migrated += 1

    conn.execute("DROP TABLE saves")

    return {
        "legacy_saves": len(rows),
        "migrated_checkpoints": migrated,
        "fill_rate_world_id": round((migrated / len(rows)), 4) if rows else 1.0,
        "anomaly_samples": anomalies[:10],
    }


def _drop_tenant_id_columns(conn: sqlite3.Connection) -> list[str]:
    table_rows = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
    ).fetchall()
    cleaned_tables: list[str] = []

    for row in table_rows:
        table_name = str(row[0])
        if _column_exists(conn, table_name, "tenant_id"):
            conn.execute(f'ALTER TABLE "{table_name}" DROP COLUMN tenant_id')
            cleaned_tables.append(table_name)

    return cleaned_tables


def _drop_obsolete_tables(conn: sqlite3.Connection) -> dict[str, Any]:
    dropped_tables: list[str] = []
    if _table_exists(conn, "tenants"):
        conn.execute("DROP TABLE tenants")
        dropped_tables.append("tenants")

    cleaned_tenant_columns = _drop_tenant_id_columns(conn)
    return {
        "dropped_tables": dropped_tables,
        "dropped_tenant_columns": cleaned_tenant_columns,
    }


def _collect_reconciliation(conn: sqlite3.Connection) -> dict[str, Any]:
    row_counts = {}
    tables = [
        "users",
        "characters",
        "worlds",
        "world_characters",
        "knowledge",
        "courses",
        "sessions",
        "checkpoints",
        "learner_profiles",
        "progress_trackings",
        "fsrs_states",
        "chat_messages",
        "teacher_personas",
    ]
    for table in tables:
        row_counts[table] = _row_count(conn, table)

    null_stats = {
        "courses.world_id": _null_count(conn, "courses", "world_id"),
        "sessions.world_id": _null_count(conn, "sessions", "world_id"),
        "sessions.sage_character_id": _null_count(conn, "sessions", "sage_character_id"),
        "sessions.relationship": _null_count(conn, "sessions", "relationship"),
        "checkpoints.world_id": _null_count(conn, "checkpoints", "world_id"),
        "checkpoints.state": _null_count(conn, "checkpoints", "state"),
        "knowledge.graph": _null_count(conn, "knowledge", "graph"),
        "learner_profiles.profile": _null_count(conn, "learner_profiles", "profile"),
    }

    tenant_columns = []
    table_rows = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
    ).fetchall()
    for row in table_rows:
        table_name = str(row[0])
        if _column_exists(conn, table_name, "tenant_id"):
            tenant_columns.append(table_name)

    legacy_tables = [
        name for name in ("subjects", "saves", "tenants")
        if _table_exists(conn, name)
    ]

    anomalies = {
        "courses_missing_world": _fetch_rows(
            conn,
            "SELECT id, name FROM courses WHERE world_id IS NULL LIMIT 10",
        )
        if _table_exists(conn, "courses") and _column_exists(conn, "courses", "world_id")
        else [],
        "sessions_missing_world": _fetch_rows(
            conn,
            "SELECT id, course_id FROM sessions WHERE world_id IS NULL LIMIT 10",
        )
        if _table_exists(conn, "sessions") and _column_exists(conn, "sessions", "world_id")
        else [],
        "knowledge_missing_rows": _fetch_rows(
            conn,
            """
            SELECT w.id AS world_id, w.name
            FROM worlds w
            LEFT JOIN knowledge k ON k.world_id = w.id
            WHERE k.world_id IS NULL
            LIMIT 10
            """,
        )
        if _table_exists(conn, "worlds") and _table_exists(conn, "knowledge")
        else [],
        "legacy_tables_present": legacy_tables,
        "tenant_columns_present": tenant_columns,
    }

    return {
        "row_counts": row_counts,
        "null_stats": null_stats,
        "anomaly_samples": anomalies,
    }


def migrate_phase1(db_path: str, report_path: str | None = None) -> dict[str, Any]:
    if not os.path.exists(db_path):
        raise FileNotFoundError(f"Database not found: {db_path}")

    backup_path = f"{db_path}.bak.{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    shutil.copy2(db_path, backup_path)

    conn = _connect(db_path)
    conn.execute("PRAGMA foreign_keys=OFF")

    report: dict[str, Any] = {
        "started_at": _utc_iso(),
        "db_path": db_path,
        "backup_path": backup_path,
    }

    try:
        report["pre_reconciliation"] = _collect_reconciliation(conn)

        conn.execute("BEGIN")

        _ensure_characters_type(conn)
        _create_world_tables(conn)

        world_result = _create_worlds_for_characters(conn)
        char_world_map = {int(k): int(v) for k, v in world_result.pop("char_world_map").items()}

        courses_result = _rebuild_courses(conn, char_world_map)

        _rebuild_lesson_plans(conn)
        _rebuild_learning_diaries(conn)

        # Build course -> world map after course rebuild.
        course_world_rows = _fetch_rows(conn, "SELECT id, world_id FROM courses")
        course_world_map = {int(r["id"]): int(r["world_id"]) for r in course_world_rows if r.get("world_id") is not None}

        learner_result = _rebuild_learner_profiles(conn, course_world_map)
        sessions_result = _rebuild_sessions(conn, course_world_map)
        progress_result = _rebuild_progress_and_fsrs(conn, course_world_map)
        checkpoint_result = _migrate_saves_to_checkpoints(conn, course_world_map)

        # Ensure one knowledge row per world after all inserts.
        conn.execute("INSERT OR IGNORE INTO knowledge(world_id, graph) SELECT id, '{}' FROM worlds")
        obsolete_result = _drop_obsolete_tables(conn)

        conn.commit()

        post_conn = _connect(db_path)
        try:
            report["post_reconciliation"] = _collect_reconciliation(post_conn)
        finally:
            post_conn.close()

        # Itemized backfill evidence mapped to issue requirements 13-16.
        report["backfill_results"] = {
            "item_13_character_world_creation": world_result,
            "item_14_course_world_backfill": {
                "courses_total": _row_count(conn, "courses") or 0,
                "courses_with_world_id": (  # type: ignore[dict-item]
                    (_null_count(conn, "courses", "world_id") or {"filled": 0})["filled"]
                ),
                "fill_rate": round(
                    (
                        ((_null_count(conn, "courses", "world_id") or {"filled": 0})["filled"])
                        / ((_row_count(conn, "courses") or 1))
                    ),
                    4,
                )
                if (_row_count(conn, "courses") or 0)
                else 1.0,
                "anomaly_samples": courses_result.get("anomaly_samples", []),
            },
            "item_15_session_world_sage_backfill": sessions_result,
            "item_16_saves_to_checkpoints": checkpoint_result,
            "item_11_tenant_cleanup": obsolete_result,
            "progress_to_fsrs_states": progress_result,
            "learner_profile_json_merge": learner_result,
        }

        report["finished_at"] = _utc_iso()
        report["status"] = "success"

        if report_path:
            Path(report_path).parent.mkdir(parents=True, exist_ok=True)
            with open(report_path, "w", encoding="utf-8") as fh:
                json.dump(report, fh, ensure_ascii=False, indent=2)

        return report

    except Exception as exc:
        conn.rollback()
        conn.close()
        shutil.copy2(backup_path, db_path)
        raise RuntimeError(
            f"Migration failed and database restored from backup: {backup_path}; reason: {exc}"
        ) from exc
    finally:
        if conn:
            conn.close()


def main() -> None:
    parser = argparse.ArgumentParser(description="Phase 1 world-schema migration for SQLite DB")
    parser.add_argument("--db", required=True, help="Path to sqlite database file")
    parser.add_argument("--report", required=False, help="Write reconciliation report JSON to this path")
    args = parser.parse_args()

    report = migrate_phase1(args.db, args.report)
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
