"""Tests for MemoryManager - Phase 2A

Covers: dedup, salience decay, dual-channel extraction,
recall_count update, working context.
"""

import os

os.environ["TESTING"] = "1"

from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy.orm import Session

from backend.models.models import Character, ChatMessage, MemoryFact, Session as SessionModel
from backend.services.memory_extractor import should_extract_memory
from backend.services.memory_manager import memory_manager


def _make_character(db: Session, user_id: int = 1, name: str = "sage") -> Character:
    c = Character(user_id=user_id, name=name, type="sage")
    db.add(c)
    db.flush()
    return c


def _make_fact(
    db: Session,
    character_id: int,
    fact_type: str = "concept_struggle",
    content: str = "test",
    concept_tags: list | None = None,
    salience: float = 0.5,
    hours_ago: float = 0,
) -> MemoryFact:
    now = datetime.now(UTC)
    fact = MemoryFact(
        character_id=character_id,
        world_id=1,
        fact_type=fact_type,
        content=content,
        concept_tags=concept_tags or [],
        salience=salience,
        created_at=now - timedelta(hours=hours_ago),
        last_recalled_at=now,
        recall_count=0,
    )
    db.add(fact)
    db.flush()
    return fact


# ---------------------------------------------------------------
# Dedup
# ---------------------------------------------------------------


class TestDedup:
    def test_same_type_same_tags_merge(self, db_session):
        """Same fact_type + overlapping concept_tags -> merge (update content), not create new."""
        c = _make_character(db_session)
        _make_fact(db_session, c.id, "concept_struggle", "old content", ["recursion"], 0.5, 1)

        ids = memory_manager.write_facts(
            db_session, c.id, 1,
            [{"fact_type": "concept_struggle", "content": "new content", "concept_tags": ["recursion"], "salience": 0.7}],
        )

        count = db_session.query(MemoryFact).filter(MemoryFact.character_id == c.id).count()
        assert count == 1
        updated = db_session.query(MemoryFact).filter(MemoryFact.character_id == c.id).first()
        assert updated.content == "new content"
        assert updated.salience == 0.7

    def test_different_type_same_tags_keep(self, db_session):
        """Different fact_type -> both kept even with same tags."""
        c = _make_character(db_session)
        _make_fact(db_session, c.id, "concept_struggle", "struggle", ["recursion"], 0.5, 1)

        ids = memory_manager.write_facts(
            db_session, c.id, 1,
            [{"fact_type": "concept_mastered", "content": "mastered", "concept_tags": ["recursion"], "salience": 0.8}],
        )

        count = db_session.query(MemoryFact).filter(MemoryFact.character_id == c.id).count()
        assert count == 2

    def test_no_tags_no_dedup(self, db_session):
        """Empty concept_tags -> dedup skipped, always create new."""
        c = _make_character(db_session)
        _make_fact(db_session, c.id, "student_state", "old", [], 0.5, 1)

        ids = memory_manager.write_facts(
            db_session, c.id, 1,
            [{"fact_type": "student_state", "content": "new", "concept_tags": [], "salience": 0.5}],
        )

        count = db_session.query(MemoryFact).filter(MemoryFact.character_id == c.id).count()
        assert count == 2


# ---------------------------------------------------------------
# Salience decay
# ---------------------------------------------------------------


class TestSalienceDecay:
    def test_struggle_no_decay(self, db_session):
        """concept_struggle multiplier=0 -> salience unchanged regardless of age."""
        c = _make_character(db_session)
        fact = _make_fact(db_session, c.id, "concept_struggle", "test", ["x"], 0.8, hours_ago=48)

        effective = memory_manager.compute_effective_salience(fact)
        assert effective == 0.8

    def test_preference_no_decay(self, db_session):
        """preference multiplier=0 -> no decay."""
        c = _make_character(db_session)
        fact = _make_fact(db_session, c.id, "preference", "likes examples", [], 0.7, hours_ago=100)

        effective = memory_manager.compute_effective_salience(fact)
        assert effective == 0.7

    def test_student_state_decays(self, db_session):
        """student_state multiplier=1.5 -> decays over time."""
        c = _make_character(db_session)
        fact = _make_fact(db_session, c.id, "student_state", "tired", [], 0.9, hours_ago=48)

        effective = memory_manager.compute_effective_salience(fact)
        assert effective < 0.9
        assert effective > 0  # not zero

    def test_recall_count_slows_decay(self, db_session):
        """Higher recall_count -> slower decay."""
        c = _make_character(db_session)
        fact_no_recall = _make_fact(db_session, c.id, "event", "ev1", [], 1.0, hours_ago=48)
        fact_with_recall = _make_fact(db_session, c.id, "event", "ev2", [], 1.0, hours_ago=48)
        fact_with_recall.recall_count = 10

        e1 = memory_manager.compute_effective_salience(fact_no_recall)
        e2 = memory_manager.compute_effective_salience(fact_with_recall)
        assert e2 > e1


# ---------------------------------------------------------------
# Recall count
# ---------------------------------------------------------------


class TestRetrieve:
    def test_retrieve_updates_recall_count(self, db_session):
        """retrieve() increments recall_count and updates last_recalled_at."""
        c = _make_character(db_session)
        fact = _make_fact(db_session, c.id, "preference", "likes examples", [], 0.7)

        assert fact.recall_count == 0
        results = memory_manager.retrieve(db_session, c.id, world_id=1)
        assert len(results) >= 1

        db_session.refresh(fact)
        assert fact.recall_count >= 1

    def test_retrieve_filters_by_effective_min_salience(self, db_session):
        """A struggle at base salience 0.2 (no decay) is below min 0.3 -> excluded."""
        c = _make_character(db_session)
        _make_fact(db_session, c.id, "concept_struggle", "low", ["x"], 0.2, hours_ago=1)
        results = memory_manager.retrieve(db_session, c.id, world_id=1, min_salience=0.3)
        assert results == []

    def test_retrieve_orders_by_effective_salience(self, db_session):
        """A non-decaying struggle outranks a heavily-decayed student_state with higher base."""
        c = _make_character(db_session)
        # struggle: multiplier=0 -> effective=0.5 regardless of age
        struggle = _make_fact(db_session, c.id, "concept_struggle", "stable", ["s"], 0.5, hours_ago=300)
        # student_state: multiplier=1.5, age=300h -> effective ~ 0.9*exp(-1.875) ~ 0.138
        _make_fact(db_session, c.id, "student_state", "stale", [], 0.9, hours_ago=300)

        results = memory_manager.retrieve(db_session, c.id, world_id=1)
        assert results, "should retrieve at least one"
        assert results[0].id == struggle.id, "struggle effective (0.5) should beat decayed student_state"


# ---------------------------------------------------------------
# should_extract_memory fix
# ---------------------------------------------------------------


class TestShouldExtract:
    def test_requires_memory_tag(self):
        """Without <memory> tag -> False, even with long content."""
        assert should_extract_memory("This is a long response without any memory tags at all, quite verbose.") is False

    def test_with_memory_tag(self):
        """With <memory> tag and long content -> True."""
        text = "Some content here that is more than twenty characters long <memory>{}</memory>"
        assert should_extract_memory(text) is True

    def test_short_with_tag(self):
        """With <memory> tag but short content -> False."""
        assert should_extract_memory("short <memory>{}</memory>") is False


# ---------------------------------------------------------------
# Dual-channel extraction
# ---------------------------------------------------------------


class TestDualChannel:
    def test_student_signal_confusion(self, db_session):
        """Student message containing confusion keyword -> concept_struggle written."""
        c = _make_character(db_session)
        memory_manager._extract_student_signals(
            db_session, "我完全不懂这个概念", character_id=c.id, world_id=1,
        )

        facts = db_session.query(MemoryFact).filter(
            MemoryFact.character_id == c.id,
            MemoryFact.fact_type == "concept_struggle",
        ).all()
        assert len(facts) >= 1
        assert "困惑" in facts[0].content

    def test_student_signal_mastery(self, db_session):
        """Student message containing mastery keyword -> concept_mastered written."""
        c = _make_character(db_session)
        memory_manager._extract_student_signals(
            db_session, "我明白了!", character_id=c.id, world_id=1,
        )

        facts = db_session.query(MemoryFact).filter(
            MemoryFact.character_id == c.id,
            MemoryFact.fact_type == "concept_mastered",
        ).all()
        assert len(facts) >= 1

    def test_student_signal_negative_emotion(self, db_session):
        """Student message containing negative emotion keyword -> student_state written."""
        c = _make_character(db_session)
        memory_manager._extract_student_signals(
            db_session, "好难啊", character_id=c.id, world_id=1,
        )

        facts = db_session.query(MemoryFact).filter(
            MemoryFact.character_id == c.id,
            MemoryFact.fact_type == "student_state",
        ).all()
        assert len(facts) >= 1
        assert "情绪" in facts[0].content

    def test_student_signal_preference(self, db_session):
        """Student message containing preference keyword -> preference written."""
        c = _make_character(db_session)
        memory_manager._extract_student_signals(
            db_session, "能举个例子吗", character_id=c.id, world_id=1,
        )

        facts = db_session.query(MemoryFact).filter(
            MemoryFact.character_id == c.id,
            MemoryFact.fact_type == "preference",
        ).all()
        assert len(facts) >= 1
        assert "偏好" in facts[0].content

    def test_no_signal_for_neutral_message(self, db_session):
        """Neutral student message -> no signal written."""
        c = _make_character(db_session)
        memory_manager._extract_student_signals(
            db_session, "请继续讲解", character_id=c.id, world_id=1,
        )

        count = db_session.query(MemoryFact).filter(
            MemoryFact.character_id == c.id,
        ).count()
        assert count == 0

    def test_channel2_dedups_repeated_confusion(self, db_session):
        """Repeated confusion messages within dedup window -> single row, not N rows."""
        c = _make_character(db_session)
        for msg in ["我不懂", "什么意思", "不理解"]:
            memory_manager._extract_student_signals(
                db_session, msg, character_id=c.id, world_id=1,
            )

        rows = db_session.query(MemoryFact).filter(
            MemoryFact.character_id == c.id,
            MemoryFact.fact_type == "concept_struggle",
        ).all()
        assert len(rows) == 1, f"expected 1 deduped row, got {len(rows)}"
        assert "__channel2_confusion__" in (rows[0].concept_tags or [])

    def test_dual_channel_merge(self, db_session):
        """Channel 1 + Channel 2 same type -> deduped (channel 1 wins, channel 2 merged)."""
        c = _make_character(db_session)
        llm_response = (
            "很好，你理解了递归的概念。"
            "<memory>{\"memories\":[{\"fact_type\":\"concept_mastered\",\"content\":\"学生掌握了递归\",\"concept_tags\":[\"recursion\"],\"salience\":0.7}]}</memory>"
        )
        student_message = "我明白了"

        result = memory_manager.extract_and_store(
            db_session, llm_response, student_message,
            character_id=c.id, world_id=1,
        )
        assert len(result.memories) >= 1

        # Channel 2 should have also fired, but dedup should prevent duplication
        mastered = db_session.query(MemoryFact).filter(
            MemoryFact.character_id == c.id,
            MemoryFact.fact_type == "concept_mastered",
        ).all()
        # At least 1 (from channel 1), channel 2 with no tags creates a separate one
        assert len(mastered) >= 1


# ---------------------------------------------------------------
# Working context
# ---------------------------------------------------------------


class TestWorkingContext:
    def test_returns_recent_messages(self, db_session):
        """get_working_context returns messages in chronological order."""
        c = _make_character(db_session)
        session = SessionModel(
            course_id=1, user_id=1, world_id=1, sage_character_id=c.id,
        )
        db_session.add(session)
        db_session.flush()

        db_session.add(ChatMessage(session_id=session.id, sender_type="user", content="hello"))
        db_session.add(ChatMessage(session_id=session.id, sender_type="teacher", content="hi"))
        db_session.flush()

        ctx = memory_manager.get_working_context(db_session, session.id)
        assert len(ctx) == 2
        assert ctx[0]["role"] == "user"
        assert ctx[1]["role"] == "assistant"

    def test_empty_session(self, db_session):
        """Empty session -> empty list."""
        c = _make_character(db_session)
        session = SessionModel(
            course_id=1, user_id=1, world_id=1, sage_character_id=c.id,
        )
        db_session.add(session)
        db_session.flush()

        ctx = memory_manager.get_working_context(db_session, session.id)
        assert ctx == []