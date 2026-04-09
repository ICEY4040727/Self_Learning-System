"""Create base tables (users, characters, worlds, etc.)

Revision ID: 2026_04_06_000
Revises: 
Create Date: 2026-04-06

This migration creates all base tables for the World system.
It must run first before any other migrations that reference these tables.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '2026_04_06_000'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create users table
    op.create_table(
        'users',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('username', sa.String(length=50), nullable=False),
        sa.Column('password_hash', sa.String(length=255), nullable=False),
        sa.Column('role', sa.String(length=20), nullable=True),
        sa.Column('encrypted_api_key', sa.String(length=255), nullable=True),
        sa.Column('default_provider', sa.String(length=50), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('username')
    )
    op.create_index(op.f('ix_users_id'), 'users', ['id'], unique=False)
    op.create_index(op.f('ix_users_username'), 'users', ['username'], unique=False)

    # Create worlds table
    op.create_table(
        'worlds',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('scenes', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_worlds_id'), 'worlds', ['id'], unique=False)

    # Create characters table
    op.create_table(
        'characters',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.Column('type', sa.String(length=20), nullable=False),
        sa.Column('avatar', sa.String(length=255), nullable=True),
        sa.Column('personality', sa.Text(), nullable=True),
        sa.Column('background', sa.Text(), nullable=True),
        sa.Column('speech_style', sa.Text(), nullable=True),
        sa.Column('sprites', sa.JSON(), nullable=True),
        sa.Column('title', sa.String(length=100), nullable=True),
        sa.Column('tags', sa.JSON(), nullable=True),
        sa.Column('experience_points', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('level', sa.Integer(), nullable=False, server_default='1'),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_characters_id'), 'characters', ['id'], unique=False)

    # Create world_characters table
    op.create_table(
        'world_characters',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('world_id', sa.Integer(), nullable=False),
        sa.Column('character_id', sa.Integer(), nullable=False),
        sa.Column('role', sa.String(length=20), nullable=False),
        sa.Column('is_primary', sa.Boolean(), nullable=True),
        sa.ForeignKeyConstraint(['world_id'], ['worlds.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['character_id'], ['characters.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('world_id', 'character_id', name='uq_world_character')
    )
    op.create_index(op.f('ix_world_characters_id'), 'world_characters', ['id'], unique=False)

    # Create knowledge table
    op.create_table(
        'knowledge',
        sa.Column('world_id', sa.Integer(), nullable=False),
        sa.Column('graph', sa.JSON(), nullable=False),
        sa.ForeignKeyConstraint(['world_id'], ['worlds.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('world_id')
    )

    # Create teacher_personas table
    op.create_table(
        'teacher_personas',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('character_id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.Column('version', sa.String(length=20), nullable=True),
        sa.Column('traits', sa.JSON(), nullable=True),
        sa.Column('system_prompt_template', sa.Text(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['character_id'], ['characters.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_teacher_personas_id'), 'teacher_personas', ['id'], unique=False)

    # Create learner_profiles table
    op.create_table(
        'learner_profiles',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('world_id', sa.Integer(), nullable=False),
        sa.Column('profile', sa.JSON(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.ForeignKeyConstraint(['world_id'], ['worlds.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_learner_profiles_id'), 'learner_profiles', ['id'], unique=False)

    # Create courses table
    op.create_table(
        'courses',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('world_id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('target_level', sa.String(length=50), nullable=True),
        sa.Column('meta', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['world_id'], ['worlds.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_courses_id'), 'courses', ['id'], unique=False)

    # Create lesson_plans table
    op.create_table(
        'lesson_plans',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('course_id', sa.Integer(), nullable=False),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['course_id'], ['courses.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_lesson_plans_id'), 'lesson_plans', ['id'], unique=False)

    # Create learning_diaries table
    op.create_table(
        'learning_diaries',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('course_id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('date', sa.DateTime(), nullable=False),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('reflection', sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(['course_id'], ['courses.id'], ),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_learning_diaries_id'), 'learning_diaries', ['id'], unique=False)

    # Create progress_trackings table
    op.create_table(
        'progress_trackings',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('course_id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('topic', sa.String(length=100), nullable=False),
        sa.Column('mastery_level', sa.Integer(), nullable=True),
        sa.Column('last_review', sa.DateTime(), nullable=True),
        sa.Column('next_review', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['course_id'], ['courses.id'], ),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_progress_trackings_id'), 'progress_trackings', ['id'], unique=False)

    # Create fsrs_states table
    op.create_table(
        'fsrs_states',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('world_id', sa.Integer(), nullable=False),
        sa.Column('concept_id', sa.String(length=150), nullable=False),
        sa.Column('difficulty', sa.Float(), nullable=True),
        sa.Column('stability', sa.Float(), nullable=True),
        sa.Column('last_review', sa.DateTime(), nullable=True),
        sa.Column('next_review', sa.DateTime(), nullable=True),
        sa.Column('reps', sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(['world_id'], ['worlds.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('world_id', 'concept_id', name='uq_fsrs_world_concept')
    )
    op.create_index(op.f('ix_fsrs_states_id'), 'fsrs_states', ['id'], unique=False)

    # Create sessions table
    op.create_table(
        'sessions',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('course_id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('world_id', sa.Integer(), nullable=False),
        sa.Column('sage_character_id', sa.Integer(), nullable=True),
        sa.Column('traveler_character_id', sa.Integer(), nullable=True),
        sa.Column('started_at', sa.DateTime(), nullable=True),
        sa.Column('ended_at', sa.DateTime(), nullable=True),
        sa.Column('system_prompt', sa.Text(), nullable=True),
        sa.Column('relationship', sa.JSON(), nullable=False),
        sa.Column('teacher_persona_id', sa.Integer(), nullable=True),
        sa.Column('learner_profile_id', sa.Integer(), nullable=True),
        sa.Column('parent_checkpoint_id', sa.Integer(), nullable=True),
        sa.Column('branch_name', sa.String(length=120), nullable=True),
        sa.ForeignKeyConstraint(['course_id'], ['courses.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.ForeignKeyConstraint(['world_id'], ['worlds.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['teacher_persona_id'], ['teacher_personas.id'], ),
        sa.ForeignKeyConstraint(['learner_profile_id'], ['learner_profiles.id'], ),
        sa.ForeignKeyConstraint(['parent_checkpoint_id'], ['checkpoints.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_sessions_id'), 'sessions', ['id'], unique=False)

    # Create chat_messages table
    op.create_table(
        'chat_messages',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('session_id', sa.Integer(), nullable=False),
        sa.Column('sender_type', sa.String(length=20), nullable=False),
        sa.Column('sender_id', sa.Integer(), nullable=True),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('timestamp', sa.DateTime(), nullable=True),
        sa.Column('emotion_analysis', sa.JSON(), nullable=True),
        sa.Column('used_memory_ids', sa.JSON(), nullable=True),
        sa.ForeignKeyConstraint(['session_id'], ['sessions.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_chat_messages_id'), 'chat_messages', ['id'], unique=False)

    # Create relationship_stages table
    op.create_table(
        'relationship_stages',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('session_id', sa.Integer(), nullable=False),
        sa.Column('stage', sa.String(length=20), nullable=False),
        sa.Column('reason', sa.Text(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['session_id'], ['sessions.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_relationship_stages_id'), 'relationship_stages', ['id'], unique=False)

    # Create checkpoints table
    op.create_table(
        'checkpoints',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('world_id', sa.Integer(), nullable=False),
        sa.Column('session_id', sa.Integer(), nullable=True),
        sa.Column('save_name', sa.String(length=100), nullable=False),
        sa.Column('message_index', sa.Integer(), nullable=False),
        sa.Column('state', sa.JSON(), nullable=False),
        sa.Column('thumbnail_path', sa.String(length=255), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.ForeignKeyConstraint(['world_id'], ['worlds.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['session_id'], ['sessions.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_checkpoints_id'), 'checkpoints', ['id'], unique=False)

    # Create saves table
    op.create_table(
        'saves',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('slot', sa.Integer(), nullable=False),
        sa.Column('world_id', sa.Integer(), nullable=True),
        sa.Column('session_id', sa.Integer(), nullable=True),
        sa.Column('checkpoint_id', sa.Integer(), nullable=True),
        sa.Column('save_data', sa.JSON(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.ForeignKeyConstraint(['world_id'], ['worlds.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['session_id'], ['sessions.id'], ),
        sa.ForeignKeyConstraint(['checkpoint_id'], ['checkpoints.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('user_id', 'slot', name='uq_save_user_slot')
    )
    op.create_index(op.f('ix_saves_id'), 'saves', ['id'], unique=False)


def downgrade() -> None:
    op.drop_table('saves')
    op.drop_table('checkpoints')
    op.drop_table('relationship_stages')
    op.drop_table('chat_messages')
    op.drop_table('sessions')
    op.drop_table('fsrs_states')
    op.drop_table('progress_trackings')
    op.drop_table('learning_diaries')
    op.drop_table('lesson_plans')
    op.drop_table('courses')
    op.drop_table('learner_profiles')
    op.drop_table('teacher_personas')
    op.drop_table('knowledge')
    op.drop_table('world_characters')
    op.drop_table('characters')
    op.drop_table('worlds')
    op.drop_table('users')
