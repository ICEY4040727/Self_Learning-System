"""Add user_profiles table for cross-world profile aggregation

Revision ID: 2026_04_06_001
Revises: 2026_04_06_000
Create Date: 2026-04-06 10:24:00.000000

NOTE: user_profiles table is now created in 2026_04_06_000 (base tables).
This migration is kept for downgrade compatibility only.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '2026_04_06_001'
down_revision: Union[str, None] = '2026_04_08_002'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # user_profiles table is now created in 2026_04_06_000 (base tables migration)
    # This migration is kept for backward compatibility only
    pass


def downgrade() -> None:
    # user_profiles is part of base tables, cannot be dropped here
    pass
