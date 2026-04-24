"""Add profile_dimension_defs table with seed data

Revision ID: 2026_04_25_profile_dims
Revises: 2026_04_25_memory_idx
Create Date: 2026-04-25
"""

import json

from alembic import op
from sqlalchemy import Boolean, Column, DateTime, Integer, JSON, String, Text, UniqueConstraint, text
from sqlalchemy.orm import Session

revision = "2026_04_25_profile_dims"
down_revision = "2026_04_25_memory_idx"
branch_labels = None
depends_on = None

SEED_DIMENSIONS = [
    {
        "key": "abstract_thinking",
        "display_name": "抽象思维",
        "category": "cognitive",
        "source_fact_types": ["concept_struggle", "concept_mastered"],
        "aggregation_method": "ratio",
        "aggregation_params": {"positive_types": ["concept_mastered"], "total_types": ["concept_struggle", "concept_mastered"]},
    },
    {
        "key": "problem_solving",
        "display_name": "问题解决",
        "category": "cognitive",
        "source_fact_types": ["concept_struggle", "concept_mastered"],
        "aggregation_method": "conversion_rate",
        "aggregation_params": {"from_type": "concept_struggle", "to_type": "concept_mastered"},
    },
    {
        "key": "self_monitoring",
        "display_name": "自我监控",
        "category": "metacognitive",
        "source_fact_types": ["student_state", "preference"],
        "aggregation_method": "keyword_extract",
        "aggregation_params": {"keywords": ["不懂", "不明白", "明白了", "理解了", "困惑"]},
    },
    {
        "key": "learning_resilience",
        "display_name": "学习韧性",
        "category": "affective",
        "source_fact_types": ["concept_struggle", "concept_mastered", "student_state"],
        "aggregation_method": "conversion_rate",
        "aggregation_params": {"from_type": "concept_struggle", "to_type": "concept_mastered"},
    },
    {
        "key": "engagement",
        "display_name": "学习投入",
        "category": "affective",
        "source_fact_types": [],
        "aggregation_method": "emotion_balance",
        "aggregation_params": {"positive_emotions": ["curiosity", "excitement", "satisfaction"], "total_emotions": ["curiosity", "excitement", "satisfaction", "frustration", "boredom", "anxiety", "confusion", "neutral"]},
    },
]


def upgrade() -> None:
    op.create_table(
        "profile_dimension_defs",
        Column("id", Integer, primary_key=True, autoincrement=True),
        Column("key", String(50), unique=True, nullable=False),
        Column("display_name", String(100), nullable=False),
        Column("category", String(30), nullable=False),
        Column("source_fact_types", JSON, nullable=True),
        Column("aggregation_method", String(20), nullable=False),
        Column("aggregation_params", JSON, nullable=True),
        Column("value_range", JSON, nullable=True, default=lambda: {"min": 0.0, "max": 1.0}),
        Column("enabled", Boolean, default=True),
        Column("created_at", DateTime),
    )

    # Seed data
    bind = op.get_bind()
    session = Session(bind=bind)
    from datetime import UTC, datetime
    now = datetime.now(UTC)
    for dim in SEED_DIMENSIONS:
        session.execute(
            text(
                "INSERT INTO profile_dimension_defs "
                "(key, display_name, category, source_fact_types, aggregation_method, aggregation_params, value_range, enabled, created_at) "
                "VALUES (:key, :display_name, :category, :source_fact_types, :aggregation_method, :aggregation_params, :value_range, :enabled, :created_at)"
            ),
            {
                **dim,
                "source_fact_types": json.dumps(dim.get("source_fact_types", [])),
                "aggregation_params": json.dumps(dim.get("aggregation_params", {})),
                "value_range": json.dumps({"min": 0.0, "max": 1.0}),
                "enabled": True,
                "created_at": now,
            },
        )
    session.commit()


def downgrade() -> None:
    op.drop_table("profile_dimension_defs")