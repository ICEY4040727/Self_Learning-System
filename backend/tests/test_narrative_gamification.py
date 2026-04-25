"""Tests for Narrative + Gamification engines - Phase 2D+2E"""

import os
os.environ["TESTING"] = "1"

from datetime import UTC, datetime

import pytest
from sqlalchemy.orm import Session

from backend.models.models import (
    Achievement,
    AchievementDef,
    Character,
    MemoryFact,
    NarrativeTriggerRule,
    World,
)
from backend.services.gamification import gamification_engine
from backend.services.narrative_engine import NarrativeEngine


# ---- Helpers ----

def _make_world(db: Session) -> World:
    w = World(id=1, user_id=1, name="TestWorld")
    db.add(w)
    db.flush()
    return w


def _make_character(db: Session) -> Character:
    c = Character(user_id=1, name="sage_test", type="sage")
    db.add(c)
    db.flush()
    return c


def _make_fact(db: Session, cid: int, fact_type: str, content: str, tags=None):
    f = MemoryFact(
        character_id=cid, world_id=1, fact_type=fact_type, content=content,
        concept_tags=tags or [], salience=0.5, created_at=datetime.now(UTC),
    )
    db.add(f)
    db.flush()
    return f


def _seed_narrative_rules(db: Session):
    rules = [
        NarrativeTriggerRule(
            trigger_type="concept_mastered",
            display_name="概念掌握",
            condition_type="fact_created",
            condition_params={"fact_type": "concept_mastered"},
            priority="high", writeback_memory=False,
            cooldown_minutes=5,
            event_template="你成功掌握了「{concept}」！",
            ui_template="toast", enabled=True,
        ),
        NarrativeTriggerRule(
            trigger_type="struggle_cascade",
            display_name="困难连锁",
            condition_type="fact_count_threshold",
            condition_params={"fact_type": "concept_struggle", "count": 3, "window_minutes": 60},
            priority="high", writeback_memory=True,
            cooldown_minutes=60,
            event_template="「{concept}」似乎是一座难以翻越的山……",
            ui_template="modal", enabled=True,
        ),
        NarrativeTriggerRule(
            trigger_type="stage_change",
            display_name="关系进阶",
            condition_type="relationship_stage_change",
            condition_params={},
            priority="medium", writeback_memory=False,
            cooldown_minutes=120,
            event_template="你和导师的关系更近了一步。",
            ui_template="toast", enabled=True,
        ),
    ]
    for r in rules:
        db.add(r)
    db.flush()


def _seed_achievement_defs(db: Session):
    defs = [
        AchievementDef(
            key="first_step", display_name="初入世界", description="完成第一次学习",
            category="milestone", condition_type="stat_threshold",
            condition_params={"stat": "total_sessions", "threshold": 1},
            rarity="common", icon="", enabled=True,
        ),
        AchievementDef(
            key="abstract_awakening", display_name="抽象思维觉醒",
            description="抽象思维维度跨越0.5",
            category="growth", condition_type="dimension_crossing",
            condition_params={"dimension": "abstract_thinking", "threshold": 0.5},
            rarity="rare", icon="", enabled=True,
        ),
        AchievementDef(
            key="kindred_spirit", display_name="心意相通",
            description="与导师关系达到「朋友」",
            category="relationship", condition_type="relationship_stage",
            condition_params={"stage": "friend"},
            rarity="rare", icon="", enabled=True,
        ),
        AchievementDef(
            key="night_owl", display_name="夜猫子",
            description="在23点后学习",
            category="hidden", condition_type="stat_threshold",
            condition_params={"stat": "late_night_session", "threshold": 1},
            rarity="rare", icon="", hidden=True, enabled=True,
        ),
    ]
    for d in defs:
        db.add(d)
    db.flush()


# ---- Narrative Tests ----

class TestNarrativeEngine:
    def test_fact_created_trigger(self, db_session):
        """concept_mastered fact_created 触发叙事事件。"""
        _make_world(db_session)
        char = _make_character(db_session)
        _seed_narrative_rules(db_session)

        facts = [_make_fact(db_session, char.id, "concept_mastered", "掌握了递归", tags=["递归"])]

        engine = NarrativeEngine()
        events = engine.check_triggers(
            db_session, user_id=1, character_id=char.id, world_id=1,
            recent_facts=facts,
        )

        assert len(events) >= 1
        mastered_events = [e for e in events if e["type"] == "concept_mastered"]
        assert len(mastered_events) == 1
        assert "递归" in mastered_events[0]["text"]

    def test_cooldown_enforcement(self, db_session):
        """冷却期内不重复触发。"""
        _make_world(db_session)
        char = _make_character(db_session)
        _seed_narrative_rules(db_session)

        facts = [_make_fact(db_session, char.id, "concept_mastered", "掌握了递归", tags=["递归"])]

        engine = NarrativeEngine()
        engine._cooldowns.clear()

        # First trigger
        events1 = engine.check_triggers(
            db_session, user_id=1, character_id=char.id, world_id=1,
            recent_facts=facts,
        )
        assert len(events1) >= 1

        # Second call within cooldown → should not trigger again
        events2 = engine.check_triggers(
            db_session, user_id=1, character_id=char.id, world_id=1,
            recent_facts=facts,
        )
        mastered_2 = [e for e in events2 if e["type"] == "concept_mastered"]
        assert len(mastered_2) == 0

    def test_template_replacement(self, db_session):
        """{concept} 变量替换。"""
        _make_world(db_session)
        char = _make_character(db_session)
        _seed_narrative_rules(db_session)

        facts = [_make_fact(db_session, char.id, "concept_mastered", "掌握了二叉树", tags=["二叉树"])]

        engine = NarrativeEngine()
        engine._cooldowns.clear()
        events = engine.check_triggers(
            db_session, user_id=1, character_id=char.id, world_id=1,
            recent_facts=facts,
        )

        mastered = [e for e in events if e["type"] == "concept_mastered"]
        assert len(mastered) == 1
        assert "二叉树" in mastered[0]["text"]

    def test_writeback_memory(self, db_session):
        """struggle_cascade writeback 写入 event 类型记忆。"""
        _make_world(db_session)
        char = _make_character(db_session)
        _seed_narrative_rules(db_session)

        # Create 3 struggle facts
        for i in range(3):
            _make_fact(db_session, char.id, "concept_struggle", f"困难{i}", tags=["指针"])

        engine = NarrativeEngine()
        engine._cooldowns.clear()
        events = engine.check_triggers(
            db_session, user_id=1, character_id=char.id, world_id=1,
            recent_facts=[],
        )

        cascade = [e for e in events if e["type"] == "struggle_cascade"]
        assert len(cascade) == 1

        # Check writeback
        event_facts = db_session.query(MemoryFact).filter(
            MemoryFact.character_id == char.id,
            MemoryFact.fact_type == "event",
        ).all()
        assert len(event_facts) >= 1

    def test_stage_change_trigger(self, db_session):
        """关系阶段变化触发叙事。"""
        _make_world(db_session)
        char = _make_character(db_session)
        _seed_narrative_rules(db_session)

        engine = NarrativeEngine()
        engine._cooldowns.clear()
        events = engine.check_triggers(
            db_session, user_id=1, character_id=char.id, world_id=1,
            current_stage="friend", prev_stage="acquaintance",
        )

        stage_events = [e for e in events if e["type"] == "stage_change"]
        assert len(stage_events) == 1

    def test_no_trigger_without_change(self, db_session):
        """关系阶段未变化 → 不触发。"""
        _make_world(db_session)
        char = _make_character(db_session)
        _seed_narrative_rules(db_session)

        engine = NarrativeEngine()
        engine._cooldowns.clear()
        events = engine.check_triggers(
            db_session, user_id=1, character_id=char.id, world_id=1,
            current_stage="friend", prev_stage="friend",
        )

        stage_events = [e for e in events if e["type"] == "stage_change"]
        assert len(stage_events) == 0


# ---- Gamification Tests ----

class TestGamificationEngine:
    def test_stat_threshold(self, db_session):
        """total_sessions >= 1 触发 first_step。"""
        _make_world(db_session)
        char = _make_character(db_session)
        _seed_achievement_defs(db_session)

        unlocks = gamification_engine.check_achievements(
            db_session, user_id=1, character_id=char.id, world_id=1,
            stats={"total_sessions": 1},
        )

        keys = [u["key"] for u in unlocks]
        assert "first_step" in keys

    def test_dimension_crossing(self, db_session):
        """维度跨越阈值触发成就。"""
        _make_world(db_session)
        char = _make_character(db_session)
        _seed_achievement_defs(db_session)

        unlocks = gamification_engine.check_achievements(
            db_session, user_id=1, character_id=char.id, world_id=1,
            dimension_scores={"abstract_thinking": 0.6},
        )

        keys = [u["key"] for u in unlocks]
        assert "abstract_awakening" in keys

    def test_idempotent(self, db_session):
        """不重复解锁。"""
        _make_world(db_session)
        char = _make_character(db_session)
        _seed_achievement_defs(db_session)

        # First unlock
        u1 = gamification_engine.check_achievements(
            db_session, user_id=1, character_id=char.id, world_id=1,
            stats={"total_sessions": 1},
        )
        assert "first_step" in [u["key"] for u in u1]

        # Second call → should not unlock again
        u2 = gamification_engine.check_achievements(
            db_session, user_id=1, character_id=char.id, world_id=1,
            stats={"total_sessions": 1},
        )
        assert "first_step" not in [u["key"] for u in u2]

    def test_hidden_not_in_locked_visible(self, db_session):
        """隐藏成就不出现在 locked_visible 中。"""
        _make_world(db_session)
        char = _make_character(db_session)
        _seed_achievement_defs(db_session)

        status = gamification_engine.get_achievements_status(
            db_session, user_id=1, character_id=char.id,
        )

        locked_keys = [a["key"] for a in status["locked_visible"]]
        assert "night_owl" not in locked_keys  # hidden

    def test_relationship_stage_achievement(self, db_session):
        """关系达到 friend 触发成就。"""
        _make_world(db_session)
        char = _make_character(db_session)
        _seed_achievement_defs(db_session)

        unlocks = gamification_engine.check_achievements(
            db_session, user_id=1, character_id=char.id, world_id=1,
            current_stage="friend",
        )

        keys = [u["key"] for u in unlocks]
        assert "kindred_spirit" in keys