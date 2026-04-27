"""[TODO-T7] add card_data JSON column for full FSRS card state

The original schema cherry-picked difficulty/stability/last_review/next_review/reps
into individual columns. py-fsrs Card.from_dict requires card_id/state/step too,
so round-tripping through the column-based representation lost information and
made every reload behave like a fresh card. card_data stores the full
Card.to_dict() payload as the authoritative source; legacy columns remain for
ad-hoc SQL queries.

Revision ID: 2026_04_27_fsrs_card_data
Revises: 2026_04_26_topic_type
Create Date: 2026-04-27
"""
from alembic import op
import sqlalchemy as sa


revision = '2026_04_27_fsrs_card_data'
down_revision = '2026_04_26_topic_type'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        'fsrs_states',
        sa.Column(
            'card_data', sa.JSON(), nullable=True,
            comment='Full py-fsrs Card.to_dict() payload (card_id, state, step, '
                    'stability, difficulty, due, last_review). Authoritative; '
                    'individual columns kept for query convenience only.',
        ),
    )


def downgrade() -> None:
    op.drop_column('fsrs_states', 'card_data')
