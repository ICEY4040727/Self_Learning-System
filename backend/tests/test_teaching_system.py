"""Tests for Teaching System (Strategy + Recall) - Phase 2C"""

import os
os.environ["TESTING"] = "1"

from datetime import UTC, datetime

import pytest
from sqlalchemy.orm import Session

from backend.models.models import (
    Character,
    Course,
    LearnerProfile,
    MemoryFact,
    StrategyRule,
    World,
)
from backend.services.prompt_builder.modules.recall_context import RecallContextModule
from backend.services.prompt_builder.modules.strategy import StrategyModule
from backend.services.recall_service import recall_service


# ---- Helpers ----

def _make_world(db: Session, user_id: int = 1) -> World:
    w = World(id=1, user_id=user_id, name="TestWorld")
    db.add(w)
    db.flush()
    return w


def _make_character(db: Session, user_id: int = 1) -> Character:
    c = Character(user_id=user_id, name="sage_test", type="sage")
    db.add(c)
    db.flush()
    return c


def _make_profile(db: Session, user_id: int = 1, world_id: int = 1, **dims) -> LearnerProfile:
    lp = LearnerProfile(
        user_id=user_id, world_id=world_id,
        profile={"preferences": {}, "affect": {}, "metacognition": {}, "dimension_scores": dims},
    )
    db.add(lp)
    db.flush()
    return lp


def _make_fact(db: Session, cid: int, fact_type: str, content: str, concept_tags: list | None = None):
    f = MemoryFact(
        character_id=cid, world_id=1, fact_type=fact_type, content=content,
        concept_tags=concept_tags or [], salience=0.5, created_at=datetime.now(UTC),
    )
    db.add(f)
    db.flush()
    return f


def _seed_rules(db: Session):
    rules = [
        StrategyRule(
            dimension_key="abstract_thinking",
            low_instruction="用具体实例辅助理解",
            mid_instruction=None,
            high_instruction="直接讨论抽象模式",
            priority=10, scene="learning", enabled=True,
        ),
        StrategyRule(
            dimension_key="problem_solving",
            low_instruction="分步骤引导",
            mid_instruction=None,
            high_instruction="鼓励自主探索",
            priority=20, scene="learning", enabled=True,
        ),
    ]
    for r in rules:
        db.add(r)
    db.flush()


# ---- StrategyModule Tests ----

class TestStrategyModule:
    def test_strategy_low(self, db_session):
        """Low dimension score (<0.4) → low_instruction injected."""
        _seed_rules(db_session)
        lp = _make_profile(db_session, abstract_thinking=0.2)

        ctx = {"db": db_session, "learner_profile": lp, "scene": "learning"}
        mod = StrategyModule()
        result = mod.assemble(ctx)

        assert result is not None
        assert "具体实例" in result

    def test_strategy_high(self, db_session):
        """High dimension score (>0.7) → high_instruction injected."""
        _seed_rules(db_session)
        lp = _make_profile(db_session, abstract_thinking=0.9)

        ctx = {"db": db_session, "learner_profile": lp, "scene": "learning"}
        mod = StrategyModule()
        result = mod.assemble(ctx)

        assert result is not None
        assert "抽象模式" in result

    def test_strategy_null_mid(self, db_session):
        """Mid range (0.4-0.7) with null mid_instruction → nothing injected for that dim."""
        _seed_rules(db_session)
        lp = _make_profile(db_session, abstract_thinking=0.5)

        ctx = {"db": db_session, "learner_profile": lp, "scene": "learning"}
        mod = StrategyModule()
        result = mod.assemble(ctx)

        # abstract_thinking mid is null → no instruction
        # but if problem_solving also has dimension_scores, check it
        assert result is None  # only abstract_thinking=0.5, mid=null → None

    def test_strategy_no_profile(self, db_session):
        """No learner_profile → should_include returns False."""
        ctx = {"db": db_session, "learner_profile": None}
        mod = StrategyModule()
        assert mod.should_include(ctx) is False

    def test_strategy_multiple_rules(self, db_session):
        """Multiple matching rules → all applicable instructions."""
        _seed_rules(db_session)
        lp = _make_profile(db_session, abstract_thinking=0.2, problem_solving=0.8)

        ctx = {"db": db_session, "learner_profile": lp, "scene": "learning"}
        mod = StrategyModule()
        result = mod.assemble(ctx)

        assert result is not None
        assert "具体实例" in result      # abstract_thinking low
        assert "自主探索" in result      # problem_solving high


# ---- RecallService Tests ----

class TestRecallService:
    def test_recall_no_topic(self, db_session):
        """No topic → empty hints."""
        hints = recall_service.get_recall_hints(
            db_session, character_id=1, world_id=1,
            current_topic=None, course_id=1,
        )
        assert hints == []

    def test_recall_no_concept_map(self, db_session):
        """No concept_map in course → empty hints."""
        w = _make_world(db_session)
        c = Course(id=1, world_id=w.id, name="TestCourse", meta={})
        db_session.add(c)
        db_session.flush()

        hints = recall_service.get_recall_hints(
            db_session, character_id=1, world_id=1,
            current_topic="tree_traversal", course_id=1,
        )
        assert hints == []

    def test_recall_prerequisite_struggle(self, db_session):
        """Prereq concept has struggle but no mastered → review hint."""
        w = _make_world(db_session)
        char = _make_character(db_session)

        concept_map = {
            "nodes": [
                {"id": "recursion", "label": "递归"},
                {"id": "tree_traversal", "label": "树遍历"},
            ],
            "edges": [
                {"source": "tree_traversal", "target": "recursion", "type": "requires"},
            ],
        }
        c = Course(id=1, world_id=w.id, name="TestCourse", meta={"concept_map": concept_map})
        db_session.add(c)
        db_session.flush()

        # Student struggled with recursion
        _make_fact(db_session, char.id, "concept_struggle", "学生对递归理解困难", concept_tags=["recursion"])

        hints = recall_service.get_recall_hints(
            db_session, character_id=char.id, world_id=1,
            current_topic="tree_traversal", course_id=1,
        )

        assert len(hints) == 1
        assert "递归" in hints[0]
        assert "复习" in hints[0]

    def test_recall_topic_not_in_nodes(self, db_session):
        """Topic not in concept_map nodes → empty hints."""
        w = _make_world(db_session)
        concept_map = {
            "nodes": [{"id": "recursion", "label": "递归"}],
            "edges": [],
        }
        c = Course(id=1, world_id=w.id, name="TestCourse", meta={"concept_map": concept_map})
        db_session.add(c)
        db_session.flush()

        hints = recall_service.get_recall_hints(
            db_session, character_id=1, world_id=1,
            current_topic="nonexistent_topic", course_id=1,
        )
        assert hints == []

    def test_recall_no_substring_false_positive(self, db_session):
        """[TODO-3] prereq 'abs' must NOT match a fact with content
        'absolutely confused' or tags ['absolute']."""
        w = _make_world(db_session)
        char = _make_character(db_session)
        concept_map = {
            "nodes": [
                {"id": "abs", "label": "abs"},
                {"id": "topic", "label": "topic"},
            ],
            "edges": [
                {"source": "topic", "target": "abs", "type": "requires"},
            ],
        }
        c = Course(id=1, world_id=w.id, name="TestCourse", meta={"concept_map": concept_map})
        db_session.add(c)
        db_session.flush()

        # A struggle fact whose content contains "abs" as substring of another word
        # and whose tags contain a tag with "abs" as substring — but neither is the
        # exact tag "abs". Old code matched both via substring; new code must not.
        _make_fact(
            db_session, char.id, "concept_struggle",
            "absolutely confused about something else",
            concept_tags=["absolute"],
        )

        hints = recall_service.get_recall_hints(
            db_session, character_id=char.id, world_id=1,
            current_topic="topic", course_id=1,
        )
        assert hints == []