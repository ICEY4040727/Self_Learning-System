"""initial schema with 13 tables

Revision ID: 001
Revises:
Create Date: 2026-03-25
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = '001'
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table('tenants',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('name', sa.String(100), nullable=False),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now()),
    )
    op.create_index('ix_tenants_id', 'tenants', ['id'])

    op.create_table('users',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('tenant_id', sa.Integer(), sa.ForeignKey('tenants.id')),
        sa.Column('username', sa.String(50), unique=True, nullable=False),
        sa.Column('password_hash', sa.String(255), nullable=False),
        sa.Column('role', sa.String(20), server_default='student'),
        sa.Column('encrypted_api_key', sa.String(255), nullable=True),
        sa.Column('default_provider', sa.String(50), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now()),
    )
    op.create_index('ix_users_id', 'users', ['id'])
    op.create_index('ix_users_username', 'users', ['username'], unique=True)

    op.create_table('characters',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('tenant_id', sa.Integer(), sa.ForeignKey('tenants.id')),
        sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id')),
        sa.Column('name', sa.String(100), nullable=False),
        sa.Column('avatar', sa.String(255), nullable=True),
        sa.Column('personality', sa.Text(), nullable=True),
        sa.Column('background', sa.Text(), nullable=True),
        sa.Column('speech_style', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now()),
    )
    op.create_index('ix_characters_id', 'characters', ['id'])

    op.create_table('teacher_personas',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('tenant_id', sa.Integer(), sa.ForeignKey('tenants.id')),
        sa.Column('character_id', sa.Integer(), sa.ForeignKey('characters.id')),
        sa.Column('name', sa.String(100), nullable=False),
        sa.Column('version', sa.String(20), server_default='1.0'),
        sa.Column('traits', sa.JSON(), nullable=True),
        sa.Column('system_prompt_template', sa.Text(), nullable=True),
        sa.Column('is_active', sa.Boolean(), server_default='false'),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.func.now()),
    )
    op.create_index('ix_teacher_personas_id', 'teacher_personas', ['id'])

    op.create_table('subjects',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('tenant_id', sa.Integer(), sa.ForeignKey('tenants.id')),
        sa.Column('character_id', sa.Integer(), sa.ForeignKey('characters.id')),
        sa.Column('name', sa.String(100), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('target_level', sa.String(50), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now()),
    )
    op.create_index('ix_subjects_id', 'subjects', ['id'])

    op.create_table('learner_profiles',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('tenant_id', sa.Integer(), sa.ForeignKey('tenants.id')),
        sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id')),
        sa.Column('subject_id', sa.Integer(), sa.ForeignKey('subjects.id'), nullable=True),
        sa.Column('learning_style', sa.JSON(), nullable=True),
        sa.Column('cognitive_traits', sa.JSON(), nullable=True),
        sa.Column('emotional_traits', sa.JSON(), nullable=True),
        sa.Column('knowledge_graph', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.func.now()),
    )
    op.create_index('ix_learner_profiles_id', 'learner_profiles', ['id'])

    op.create_table('lesson_plans',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('subject_id', sa.Integer(), sa.ForeignKey('subjects.id')),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now()),
    )
    op.create_index('ix_lesson_plans_id', 'lesson_plans', ['id'])

    op.create_table('learning_diaries',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('subject_id', sa.Integer(), sa.ForeignKey('subjects.id')),
        sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id')),
        sa.Column('date', sa.DateTime(), nullable=False),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('reflection', sa.Text(), nullable=True),
    )
    op.create_index('ix_learning_diaries_id', 'learning_diaries', ['id'])

    op.create_table('progress_trackings',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('subject_id', sa.Integer(), sa.ForeignKey('subjects.id')),
        sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id')),
        sa.Column('topic', sa.String(100), nullable=False),
        sa.Column('mastery_level', sa.Integer(), server_default='0'),
        sa.Column('last_review', sa.DateTime(), nullable=True),
        sa.Column('next_review', sa.DateTime(), nullable=True),
        sa.Column('fsrs_state', sa.JSON(), nullable=True),
    )
    op.create_index('ix_progress_trackings_id', 'progress_trackings', ['id'])

    op.create_table('sessions',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('tenant_id', sa.Integer(), sa.ForeignKey('tenants.id')),
        sa.Column('subject_id', sa.Integer(), sa.ForeignKey('subjects.id')),
        sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id')),
        sa.Column('started_at', sa.DateTime(), server_default=sa.func.now()),
        sa.Column('ended_at', sa.DateTime(), nullable=True),
        sa.Column('system_prompt', sa.Text(), nullable=True),
        sa.Column('relationship_stage', sa.String(20), server_default='stranger'),
        sa.Column('teacher_persona_id', sa.Integer(), sa.ForeignKey('teacher_personas.id'), nullable=True),
        sa.Column('learner_profile_id', sa.Integer(), sa.ForeignKey('learner_profiles.id'), nullable=True),
    )
    op.create_index('ix_sessions_id', 'sessions', ['id'])

    op.create_table('chat_messages',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('session_id', sa.Integer(), sa.ForeignKey('sessions.id')),
        sa.Column('sender_type', sa.String(20), nullable=False),
        sa.Column('sender_id', sa.Integer(), nullable=True),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('timestamp', sa.DateTime(), server_default=sa.func.now()),
        sa.Column('emotion_analysis', sa.JSON(), nullable=True),
        sa.Column('used_memory_ids', sa.JSON(), nullable=True),
    )
    op.create_index('ix_chat_messages_id', 'chat_messages', ['id'])

    op.create_table('relationship_stages',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('session_id', sa.Integer(), sa.ForeignKey('sessions.id')),
        sa.Column('stage', sa.String(20), nullable=False),
        sa.Column('reason', sa.Text(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.func.now()),
    )
    op.create_index('ix_relationship_stages_id', 'relationship_stages', ['id'])

    op.create_table('saves',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id')),
        sa.Column('subject_id', sa.Integer(), sa.ForeignKey('subjects.id')),
        sa.Column('session_id', sa.Integer(), sa.ForeignKey('sessions.id'), nullable=True),
        sa.Column('save_name', sa.String(100), nullable=False),
        sa.Column('file_path', sa.String(255), nullable=False),
        sa.Column('memory_ids', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now()),
    )
    op.create_index('ix_saves_id', 'saves', ['id'])


def downgrade() -> None:
    op.drop_table('saves')
    op.drop_table('relationship_stages')
    op.drop_table('chat_messages')
    op.drop_table('sessions')
    op.drop_table('progress_trackings')
    op.drop_table('learning_diaries')
    op.drop_table('lesson_plans')
    op.drop_table('learner_profiles')
    op.drop_table('subjects')
    op.drop_table('teacher_personas')
    op.drop_table('characters')
    op.drop_table('users')
    op.drop_table('tenants')
