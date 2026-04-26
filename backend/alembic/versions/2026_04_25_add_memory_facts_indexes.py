"""Add indexes for memory_facts retrieval and dedup

Revision ID: 2026_04_25_memory_idx
Revises: 2026_04_14_add_checkpoint_file_path
Create Date: 2026-04-25
"""

from alembic import op

revision = "2026_04_25_memory_idx"
down_revision = "3f7e10f713f3"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_index(
        "idx_memory_facts_retrieve",
        "memory_facts",
        ["character_id", "fact_type", "salience"],
    )
    op.create_index(
        "idx_memory_facts_dedup",
        "memory_facts",
        ["character_id", "fact_type", "created_at"],
    )


def downgrade() -> None:
    op.drop_index("idx_memory_facts_dedup", table_name="memory_facts")
    op.drop_index("idx_memory_facts_retrieve", table_name="memory_facts")