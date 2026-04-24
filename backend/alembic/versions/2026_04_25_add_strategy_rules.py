"""Add strategy_rules table with seed data

Revision ID: 2026_04_25_strategy_rules
Revises: 2026_04_25_profile_dims
Create Date: 2026-04-25
"""

from alembic import op
from sqlalchemy import Boolean, Column, Integer, String, Text, text
from sqlalchemy.orm import Session

revision = "2026_04_25_strategy_rules"
down_revision = "2026_04_25_profile_dims"
branch_labels = None
depends_on = None

SEED_RULES = [
    {
        "dimension_key": "abstract_thinking",
        "low_instruction": "学生抽象思维较弱，请多用具体实例和类比辅助理解，避免纯理论推演。",
        "mid_instruction": None,
        "high_instruction": "学生抽象思维较强，可以直接讨论抽象模式，适当引入理论推导。",
        "priority": 10,
        "scene": "learning",
    },
    {
        "dimension_key": "problem_solving",
        "low_instruction": "学生问题解决能力较弱，请分步骤引导，每步确认学生理解后再继续。",
        "mid_instruction": None,
        "high_instruction": "学生问题解决能力较强，鼓励自主探索，减少步骤提示。",
        "priority": 20,
        "scene": "learning",
    },
    {
        "dimension_key": "self_monitoring",
        "low_instruction": "学生自我监控能力较弱，请主动询问是否理解，定期检查学习效果。",
        "mid_instruction": None,
        "high_instruction": "学生自我监控能力较强，引导学生自评学习效果。",
        "priority": 30,
        "scene": "learning",
    },
    {
        "dimension_key": "learning_resilience",
        "low_instruction": "学生遇到困难容易放弃，请额外鼓励，适当降低难度，拆分为更小的步骤。",
        "mid_instruction": None,
        "high_instruction": "学生学习韧性强，可以挑战更难的问题，适当增加挑战。",
        "priority": 40,
        "scene": "learning",
    },
]


def upgrade() -> None:
    op.create_table(
        "strategy_rules",
        Column("id", Integer, primary_key=True, autoincrement=True),
        Column("dimension_key", String(50), nullable=False),
        Column("low_instruction", Text, nullable=True),
        Column("mid_instruction", Text, nullable=True),
        Column("high_instruction", Text, nullable=True),
        Column("priority", Integer, default=0),
        Column("scene", String(20), default="all"),
        Column("enabled", Boolean, default=True),
    )

    bind = op.get_bind()
    session = Session(bind=bind)
    for rule in SEED_RULES:
        session.execute(
            text(
                "INSERT INTO strategy_rules "
                "(dimension_key, low_instruction, mid_instruction, high_instruction, priority, scene, enabled) "
                "VALUES (:dimension_key, :low_instruction, :mid_instruction, :high_instruction, :priority, :scene, :enabled)"
            ),
            {**rule, "enabled": True},
        )
    session.commit()


def downgrade() -> None:
    op.drop_table("strategy_rules")