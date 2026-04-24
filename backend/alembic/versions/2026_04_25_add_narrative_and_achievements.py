"""Add narrative_trigger_rules + achievement_defs + achievements

Revision ID: 2026_04_25_narrative_achievements
Revises: 2026_04_25_strategy_rules
Create Date: 2026-04-25
"""

from alembic import op
from sqlalchemy import Boolean, Column, DateTime, Integer, String, Text, UniqueConstraint, text
from sqlalchemy.orm import Session

revision = "2026_04_25_narrative_achievements"
down_revision = "2026_04_25_strategy_rules"
branch_labels = None
depends_on = None

NARRATIVE_SEEDS = [
    {
        "trigger_type": "concept_mastered",
        "display_name": "概念掌握",
        "condition_type": "fact_created",
        "condition_params": '{"fact_type": "concept_mastered"}',
        "priority": "high",
        "writeback_memory": False,
        "cooldown_minutes": 5,
        "event_template": "你成功掌握了「{concept}」！",
        "ui_template": "toast",
    },
    {
        "trigger_type": "struggle_cascade",
        "display_name": "困难连锁",
        "condition_type": "fact_count_threshold",
        "condition_params": '{"fact_type": "concept_struggle", "count": 3, "window_minutes": 60}',
        "priority": "high",
        "writeback_memory": True,
        "cooldown_minutes": 60,
        "event_template": "「{concept}」似乎是一座难以翻越的山……",
        "ui_template": "modal",
    },
    {
        "trigger_type": "breakthrough",
        "display_name": "突破时刻",
        "condition_type": "fact_created",
        "condition_params": '{"fact_type": "concept_mastered", "requires_prior_struggle": true}',
        "priority": "high",
        "writeback_memory": True,
        "cooldown_minutes": 30,
        "event_template": "经历了重重困难，你终于征服了「{concept}」！",
        "ui_template": "modal",
    },
    {
        "trigger_type": "stage_change",
        "display_name": "关系进阶",
        "condition_type": "relationship_stage_change",
        "condition_params": "{}",
        "priority": "medium",
        "writeback_memory": False,
        "cooldown_minutes": 120,
        "event_template": "你和导师的关系更近了一步。",
        "ui_template": "toast",
    },
    {
        "trigger_type": "welcome_back",
        "display_name": "欢迎回来",
        "condition_type": "time_gap",
        "condition_params": '{"min_days": 3}',
        "priority": "low",
        "writeback_memory": False,
        "cooldown_minutes": 1440,
        "event_template": "好久不见！欢迎回到这个世界。",
        "ui_template": "toast",
    },
]

ACHIEVEMENT_SEEDS = [
    {
        "key": "first_step",
        "display_name": "初入世界",
        "description": "完成第一次学习",
        "category": "milestone",
        "condition_type": "stat_threshold",
        "condition_params": '{"stat": "total_sessions", "threshold": 1}',
        "rarity": "common",
        "icon": "🌱",
    },
    {
        "key": "regular_visitor",
        "display_name": "常客",
        "description": "完成10次学习",
        "category": "milestone",
        "condition_type": "stat_threshold",
        "condition_params": '{"stat": "total_sessions", "threshold": 10}',
        "rarity": "common",
        "icon": "📚",
    },
    {
        "key": "knowledge_seeker",
        "display_name": "求知若渴",
        "description": "掌握5个概念",
        "category": "milestone",
        "condition_type": "stat_threshold",
        "condition_params": '{"stat": "concepts_mastered", "threshold": 5}',
        "rarity": "common",
        "icon": "🎯",
    },
    {
        "key": "abstract_awakening",
        "display_name": "抽象思维觉醒",
        "description": "抽象思维维度跨越0.5",
        "category": "growth",
        "condition_type": "dimension_crossing",
        "condition_params": '{"dimension": "abstract_thinking", "threshold": 0.5}',
        "rarity": "rare",
        "icon": "🧠",
    },
    {
        "key": "learn_from_setback",
        "display_name": "吃一堑长一智",
        "description": "在曾遇到困难的概念上取得突破",
        "category": "resilience",
        "condition_type": "fact_transition",
        "condition_params": '{"from": "concept_struggle", "to": "concept_mastered"}',
        "rarity": "rare",
        "icon": "💪",
    },
    {
        "key": "kindred_spirit",
        "display_name": "心意相通",
        "description": "与导师关系达到「朋友」",
        "category": "relationship",
        "condition_type": "relationship_stage",
        "condition_params": '{"stage": "friend"}',
        "rarity": "rare",
        "icon": "🤝",
    },
    {
        "key": "night_owl",
        "display_name": "夜猫子",
        "description": "在23点后学习",
        "category": "hidden",
        "condition_type": "stat_threshold",
        "condition_params": '{"stat": "late_night_session", "threshold": 1}',
        "rarity": "rare",
        "icon": "🦉",
        "hidden": True,
    },
]


def upgrade() -> None:
    # --- Narrative trigger rules ---
    op.create_table(
        "narrative_trigger_rules",
        Column("id", Integer, primary_key=True, autoincrement=True),
        Column("trigger_type", String(50), unique=True, nullable=False),
        Column("display_name", String(100), nullable=False),
        Column("condition_type", String(30), nullable=False),
        Column("condition_params", Text, nullable=True),
        Column("priority", String(10), default="medium"),
        Column("writeback_memory", Boolean, default=False),
        Column("cooldown_minutes", Integer, default=60),
        Column("event_template", Text, nullable=True),
        Column("prompt_template", Text, nullable=True),
        Column("ui_template", String(20), default="toast"),
        Column("enabled", Boolean, default=True),
    )

    bind = op.get_bind()
    session = Session(bind=bind)
    for seed in NARRATIVE_SEEDS:
        session.execute(
            text(
                "INSERT INTO narrative_trigger_rules "
                "(trigger_type, display_name, condition_type, condition_params, priority, "
                "writeback_memory, cooldown_minutes, event_template, ui_template, enabled) "
                "VALUES (:trigger_type, :display_name, :condition_type, :condition_params, :priority, "
                ":writeback_memory, :cooldown_minutes, :event_template, :ui_template, :enabled)"
            ),
            {**seed, "enabled": True},
        )

    # --- Achievement definitions ---
    op.create_table(
        "achievement_defs",
        Column("id", Integer, primary_key=True, autoincrement=True),
        Column("key", String(50), unique=True, nullable=False),
        Column("display_name", String(100), nullable=False),
        Column("description", Text, nullable=True),
        Column("category", String(20), nullable=False),
        Column("condition_type", String(30), nullable=False),
        Column("condition_params", Text, nullable=True),
        Column("rarity", String(10), default="common"),
        Column("icon", String(50), nullable=True),
        Column("hidden", Boolean, default=False),
        Column("enabled", Boolean, default=True),
    )

    for seed in ACHIEVEMENT_SEEDS:
        session.execute(
            text(
                "INSERT INTO achievement_defs "
                "(key, display_name, description, category, condition_type, condition_params, rarity, icon, hidden, enabled) "
                "VALUES (:key, :display_name, :description, :category, :condition_type, :condition_params, :rarity, :icon, :hidden, :enabled)"
            ),
            {**seed, "hidden": seed.get("hidden", False), "enabled": True},
        )

    # --- Achievement unlock records ---
    op.create_table(
        "achievements",
        Column("id", Integer, primary_key=True, autoincrement=True),
        Column("user_id", Integer, nullable=False),
        Column("character_id", Integer, nullable=False),
        Column("achievement_key", String(50), nullable=False),
        Column("unlocked_at", DateTime, nullable=True),
        Column("context", Text, nullable=True),
        UniqueConstraint("user_id", "character_id", "achievement_key", name="uq_user_char_achievement"),
    )

    session.commit()


def downgrade() -> None:
    op.drop_table("achievements")
    op.drop_table("achievement_defs")
    op.drop_table("narrative_trigger_rules")