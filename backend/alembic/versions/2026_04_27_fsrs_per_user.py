"""[TR-B1+B2+B3] FSRSState becomes per-(user, concept) cross-world

The original schema keyed FSRSState by (world_id, concept_id), which made the
spaced-repetition state for "递归" learned in one world invisible from another
world for the same user. The product semantic is cross-world: one user, one
review schedule per concept, regardless of which world they're playing in.

Migration steps:
  1. Add user_id column (nullable initially for backfill).
  2. Backfill user_id from worlds.user_id.
  3. Merge duplicate (user_id, concept_id) rows (decision C math merge):
       stability  = max(stability_a, stability_b)
       difficulty = min(difficulty_a, difficulty_b)
       reps       = sum
       last/next  = max
       card_data  = take row with higher stability, override merged fields
       world_id   = take from the higher-stability row (diagnostic)
  4. Swap UNIQUE constraint from (world_id, concept_id) to (user_id, concept_id).
  5. Make user_id NOT NULL; world_id becomes nullable (kept as diagnostic).

Revision ID: 2026_04_27_fsrs_per_user
Revises: 2026_04_27_concept_mastery
Create Date: 2026-04-27
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.sql import column, select, table


revision = '2026_04_27_fsrs_per_user'
down_revision = '2026_04_27_concept_mastery'
branch_labels = None
depends_on = None


def _merge_duplicates(conn) -> None:
    """Decision C math merge for any duplicate (user_id, concept_id) rows.

    Doing this in Python (vs raw SQL) keeps the merge math obvious; the
    expected duplicate count post-backfill is at most O(N_worlds_per_user *
    N_concepts), which is small.
    """
    fsrs = table(
        'fsrs_states',
        column('id', sa.Integer),
        column('world_id', sa.Integer),
        column('user_id', sa.Integer),
        column('concept_id', sa.String),
        column('difficulty', sa.Float),
        column('stability', sa.Float),
        column('last_review', sa.DateTime),
        column('next_review', sa.DateTime),
        column('reps', sa.Integer),
        column('card_data', sa.JSON),
    )

    rows = conn.execute(
        select(
            fsrs.c.id, fsrs.c.world_id, fsrs.c.user_id, fsrs.c.concept_id,
            fsrs.c.difficulty, fsrs.c.stability, fsrs.c.last_review,
            fsrs.c.next_review, fsrs.c.reps, fsrs.c.card_data,
        ).where(fsrs.c.user_id.isnot(None)).order_by(
            fsrs.c.user_id, fsrs.c.concept_id, fsrs.c.id,
        )
    ).mappings().all()

    groups: dict[tuple[int, str], list[dict]] = {}
    for r in rows:
        groups.setdefault((r["user_id"], r["concept_id"]), []).append(dict(r))

    for group in groups.values():
        if len(group) <= 1:
            continue

        def stab(g):
            s = g.get("stability")
            return s if s is not None else float("-inf")

        winner = max(group, key=stab)
        losers = [g for g in group if g["id"] != winner["id"]]

        stabilities = [g["stability"] for g in group if g["stability"] is not None]
        difficulties = [g["difficulty"] for g in group if g["difficulty"] is not None]
        last_reviews = [g["last_review"] for g in group if g["last_review"] is not None]
        next_reviews = [g["next_review"] for g in group if g["next_review"] is not None]

        merged_stability = max(stabilities) if stabilities else None
        merged_difficulty = min(difficulties) if difficulties else None
        merged_reps = sum((g["reps"] or 0) for g in group)
        merged_last = max(last_reviews) if last_reviews else None
        merged_next = max(next_reviews) if next_reviews else None

        merged_card = dict(winner.get("card_data") or {})
        if merged_stability is not None:
            merged_card["stability"] = merged_stability
        if merged_difficulty is not None:
            merged_card["difficulty"] = merged_difficulty

        conn.execute(
            fsrs.update().where(fsrs.c.id == winner["id"]).values(
                stability=merged_stability,
                difficulty=merged_difficulty,
                reps=merged_reps,
                last_review=merged_last,
                next_review=merged_next,
                card_data=(merged_card or None),
            )
        )
        loser_ids = [g["id"] for g in losers]
        if loser_ids:
            conn.execute(fsrs.delete().where(fsrs.c.id.in_(loser_ids)))


def upgrade() -> None:
    bind = op.get_bind()

    # 1. Add user_id column (nullable for backfill)
    op.add_column(
        'fsrs_states',
        sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id'), nullable=True),
    )

    # 2. Backfill user_id from worlds.user_id
    op.execute(
        """
        UPDATE fsrs_states
        SET user_id = (SELECT user_id FROM worlds WHERE worlds.id = fsrs_states.world_id)
        WHERE user_id IS NULL
        """
    )

    # 3. Merge duplicate (user_id, concept_id) rows (decision C)
    _merge_duplicates(bind)

    # 4 + 5. Swap UNIQUE constraint and adjust nullability.
    # Use batch_alter_table for SQLite compatibility — Postgres handles this
    # natively but the same code works on both.
    with op.batch_alter_table('fsrs_states') as batch_op:
        batch_op.drop_constraint('uq_fsrs_world_concept', type_='unique')
        batch_op.alter_column('user_id', nullable=False)
        batch_op.alter_column('world_id', nullable=True)
        batch_op.create_unique_constraint(
            'uq_fsrs_user_concept', ['user_id', 'concept_id']
        )

    op.create_index('ix_fsrs_states_user', 'fsrs_states', ['user_id'])


def downgrade() -> None:
    op.drop_index('ix_fsrs_states_user', table_name='fsrs_states')
    with op.batch_alter_table('fsrs_states') as batch_op:
        batch_op.drop_constraint('uq_fsrs_user_concept', type_='unique')
        batch_op.alter_column('world_id', nullable=False)
        batch_op.create_unique_constraint(
            'uq_fsrs_world_concept', ['world_id', 'concept_id']
        )
    op.drop_column('fsrs_states', 'user_id')
