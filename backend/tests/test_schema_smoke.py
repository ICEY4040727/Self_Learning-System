"""Schema smoke tests for SQLite create_all() tables and critical constraints."""

from sqlalchemy import inspect


EXPECTED_TABLES = {
    "users",
    "worlds",
    "world_characters",
    "characters",
    "knowledge",
    "teacher_personas",
    "learner_profiles",
    "courses",
    "lesson_plans",
    "learning_diaries",
    "progress_trackings",
    "fsrs_states",
    "sessions",
    "chat_messages",
    "relationship_stages",
    "checkpoints",
}


def _columns_by_name(inspector, table_name: str) -> dict:
    return {col["name"]: col for col in inspector.get_columns(table_name)}


class TestSchemaSmoke:
    def test_expected_tables_exist(self, db_session):
        inspector = inspect(db_session.bind)
        tables = set(inspector.get_table_names())
        assert EXPECTED_TABLES.issubset(tables)

    def test_critical_columns_exist(self, db_session):
        inspector = inspect(db_session.bind)

        users = _columns_by_name(inspector, "users")
        assert "id" in users
        assert "username" in users

        worlds = _columns_by_name(inspector, "worlds")
        assert "id" in worlds
        assert "user_id" in worlds
        assert "scenes" in worlds

        courses = _columns_by_name(inspector, "courses")
        assert "id" in courses
        assert "world_id" in courses
        assert "name" in courses

        sessions = _columns_by_name(inspector, "sessions")
        assert "id" in sessions
        assert "course_id" in sessions
        assert "world_id" in sessions
        assert "relationship" in sessions

        checkpoints = _columns_by_name(inspector, "checkpoints")
        assert "id" in checkpoints
        assert "world_id" in checkpoints
        assert "state" in checkpoints

    def test_required_fk_not_null_constraints(self, db_session):
        inspector = inspect(db_session.bind)

        assert _columns_by_name(inspector, "characters")["user_id"]["nullable"] is False
        assert _columns_by_name(inspector, "sessions")["user_id"]["nullable"] is False
        assert _columns_by_name(inspector, "sessions")["course_id"]["nullable"] is False
        assert _columns_by_name(inspector, "learner_profiles")["user_id"]["nullable"] is False
        assert _columns_by_name(inspector, "learning_diaries")["user_id"]["nullable"] is False
        assert _columns_by_name(inspector, "progress_trackings")["user_id"]["nullable"] is False

    def test_optional_session_links_remain_nullable(self, db_session):
        inspector = inspect(db_session.bind)
        session_columns = _columns_by_name(inspector, "sessions")

        assert session_columns["sage_character_id"]["nullable"] is True
        assert session_columns["traveler_character_id"]["nullable"] is True
        assert session_columns["teacher_persona_id"]["nullable"] is True
        assert session_columns["learner_profile_id"]["nullable"] is True
        assert session_columns["parent_checkpoint_id"]["nullable"] is True
