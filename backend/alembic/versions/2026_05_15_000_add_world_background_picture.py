"""Add world.background_picture column.

Revision ID: 2026_05_15_000
Revises: 2026_05_12_000
Create Date: 2026-05-15 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa
import json


revision = "2026_05_15_000"
down_revision = "2026_05_12_000"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("worlds", sa.Column("background_picture", sa.String(length=255), nullable=True))
    conn = op.get_bind()
    rows = conn.execute(sa.text("SELECT id, scenes, background_picture FROM worlds")).fetchall()
    for row in rows:
        if row.background_picture:
            continue
        scenes = row.scenes or {}
        if isinstance(scenes, str):
            try:
                scenes = json.loads(scenes)
            except json.JSONDecodeError:
                scenes = {}
        if not isinstance(scenes, dict):
            scenes = {}
        background = scenes.get("background_picture") or scenes.get("background")
        if background:
            conn.execute(
                sa.text("UPDATE worlds SET background_picture = :background WHERE id = :id"),
                {"background": background, "id": row.id},
            )


def downgrade() -> None:
    op.drop_column("worlds", "background_picture")
