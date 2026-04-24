"""Tests for ProfileAggregator - Phase 2B"""

import os
os.environ["TESTING"] = "1"

from datetime import UTC, datetime

import pytest
from sqlalchemy.orm import Session

from backend.models.models import (
    Character,
    LearnerProfile,
    MemoryFact,
    ProfileDimensionDef,
)
from backend.services.profile_aggregator import profile_aggregator


def _make_character(db: Session, user_id: int = 1) -> Character:
    c = Character(user_id=user_id, name="sage_test", type="sage")
    db.add(c)
    db.flush()
    return c


def _make_profile(db: Session, user_id: int = 1, world_id: int = 1) -> LearnerProfile:
    lp = LearnerProfile(user_id=user_id, world_id=world_id, profile={"preferences": {}, "affect": {}, "metacognition": {}})
    db.add(lp)
    db.flush()
    return lp


def _make_fact(
    db: Session, character_id: int, fact_type: str, content: str = "test", world_id: int = 1,
) -> MemoryFact:
    f = MemoryFact(
        character_id=character_id,
        world_id=world_id,
        fact_type=fact_type,
        content=content,
        salience=0.5,
        created_at=datetime.now(UTC),
    )
    db.add(f)
    db.flush()
    return f


def _seed_dimensions(db: Session) -> list[ProfileDimensionDef]:
    dims = [
        ProfileDimensionDef(
            key="abstract_thinking", display_name="抽象思维", category="cognitive",
            source_fact_types=["concept_struggle", "concept_mastered"],
            aggregation_method="ratio",
            aggregation_params={"positive_types": ["concept_mastered"], "total_types": ["concept_struggle", "concept_mastered"]},
            enabled=True,
        ),
        ProfileDimensionDef(
            key="problem_solving", display_name="问题解决", category="cognitive",
            source_fact_types=["concept_struggle", "concept_mastered"],
            aggregation_method="conversion_rate",
            aggregation_params={"from_type": "concept_struggle", "to_type": "concept_mastered"},
            enabled=True,
        ),
        ProfileDimensionDef(
            key="engagement", display_name="学习投入", category="affective",
            source_fact_types=[],
            aggregation_method="emotion_balance",
            aggregation_params={
                "positive_emotions": ["curiosity", "excitement", "satisfaction"],
                "total_emotions": ["curiosity", "excitement", "satisfaction", "frustration", "boredom", "anxiety", "confusion", "neutral"],
            },
            enabled=True,
        ),
    ]
    for d in dims:
        db.add(d)
    db.flush()
    return dims


class TestProfileMergeWrite:
    def test_merge_preserves_other_fields(self, db_session):
        """Merge write: aggregator should not overwrite preferences/affect/metacognition."""
        c = _make_character(db_session)
        lp = _make_profile(db_session)
        lp.profile = {
            "preferences": {"example_first": True},
            "affect": {"count_curiosity": 5},
            "metacognition": {"self_confidence": 0.8},
        }
        db_session.flush()

        _seed_dimensions(db_session)

        # Need enough facts to pass hallucination guard
        for _ in range(4):
            _make_fact(db_session, c.id, "concept_mastered")

        result = profile_aggregator.aggregate(
            db_session, character_id=c.id, world_id=1, user_id=1,
        )

        assert result is not None
        # preferences preserved
        assert result["preferences"]["example_first"] is True
        # affect preserved
        assert result["affect"]["count_curiosity"] == 5
        # metacognition preserved
        assert result["metacognition"]["self_confidence"] == 0.8
        # new fields added
        assert "dimension_scores" in result
        assert "learning_stats" in result


class TestAggregatorRatio:
    def test_ratio_computation(self, db_session):
        """ratio = mastered / (struggle + mastered)"""
        c = _make_character(db_session)
        lp = _make_profile(db_session)
        _seed_dimensions(db_session)

        # 3 struggle + 7 mastered = 0.7
        for _ in range(3):
            _make_fact(db_session, c.id, "concept_struggle")
        for _ in range(7):
            _make_fact(db_session, c.id, "concept_mastered")

        result = profile_aggregator.aggregate(
            db_session, character_id=c.id, world_id=1, user_id=1,
        )

        assert result is not None
        score = result["dimension_scores"]["abstract_thinking"]
        assert score == 0.7


class TestAggregatorConversionRate:
    def test_conversion_rate(self, db_session):
        """conversion_rate = mastered / (struggle + mastered)"""
        c = _make_character(db_session)
        lp = _make_profile(db_session)
        _seed_dimensions(db_session)

        for _ in range(2):
            _make_fact(db_session, c.id, "concept_struggle")
        for _ in range(3):
            _make_fact(db_session, c.id, "concept_mastered")

        result = profile_aggregator.aggregate(
            db_session, character_id=c.id, world_id=1, user_id=1,
        )

        assert result is not None
        score = result["dimension_scores"]["problem_solving"]
        assert score == 0.6  # 3 / (2+3)


class TestAggregatorHallucinationGuard:
    def test_below_threshold_no_update(self, db_session):
        """< 3 facts → dimension not updated"""
        c = _make_character(db_session)
        lp = _make_profile(db_session)
        _seed_dimensions(db_session)

        # Only 2 facts — below hallucination guard threshold of 3
        _make_fact(db_session, c.id, "concept_mastered")
        _make_fact(db_session, c.id, "concept_mastered")

        result = profile_aggregator.aggregate(
            db_session, character_id=c.id, world_id=1, user_id=1,
        )

        assert result is not None
        # abstract_thinking should not be in dimension_scores (below threshold)
        assert "abstract_thinking" not in result.get("dimension_scores", {})


class TestStrengthsWeaknesses:
    def test_strengths_and_weaknesses(self, db_session):
        """strengths > 0.7, weaknesses < 0.4"""
        c = _make_character(db_session)
        lp = _make_profile(db_session)
        _seed_dimensions(db_session)

        # 9 mastered + 1 struggle = 0.9 → strength
        for _ in range(1):
            _make_fact(db_session, c.id, "concept_struggle")
        for _ in range(9):
            _make_fact(db_session, c.id, "concept_mastered")

        result = profile_aggregator.aggregate(
            db_session, character_id=c.id, world_id=1, user_id=1,
        )

        assert result is not None
        assert "abstract_thinking" in result.get("strengths", [])
        assert "abstract_thinking" not in result.get("weaknesses", [])


class TestEmotionBalance:
    def test_emotion_balance(self, db_session):
        """emotion_balance from profile affect data"""
        c = _make_character(db_session)
        lp = _make_profile(db_session)
        _seed_dimensions(db_session)

        # Set affect data directly
        profile = dict(lp.profile)
        profile["affect"] = {
            "count_curiosity": 5,
            "count_excitement": 3,
            "count_frustration": 2,
        }
        lp.profile = profile
        db_session.flush()

        # Need enough facts for other dimensions
        for _ in range(5):
            _make_fact(db_session, c.id, "concept_mastered")

        result = profile_aggregator.aggregate(
            db_session, character_id=c.id, world_id=1, user_id=1,
        )

        assert result is not None
        # engagement = (5+3) / (5+3+2) = 0.8
        engagement = result["dimension_scores"].get("engagement")
        assert engagement is not None
        assert engagement == 0.8


class TestLearningStats:
    def test_learning_stats(self, db_session):
        """learning_stats counts mastered and struggling"""
        c = _make_character(db_session)
        lp = _make_profile(db_session)
        _seed_dimensions(db_session)

        for _ in range(5):
            _make_fact(db_session, c.id, "concept_mastered")
        for _ in range(2):
            _make_fact(db_session, c.id, "concept_struggle")

        result = profile_aggregator.aggregate(
            db_session, character_id=c.id, world_id=1, user_id=1,
        )

        assert result is not None
        stats = result["learning_stats"]
        assert stats["concepts_mastered"] == 5
        assert stats["concepts_struggling"] == 2