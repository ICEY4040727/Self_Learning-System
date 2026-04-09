"""Tests for memory_facts service - P1 #183

验证 seed memories 正确写入 memory_facts 表。
"""

import pytest
from sqlalchemy.orm import Session

from backend.models.models import Character, LearnerProfile, MemoryFact, World
from backend.services.memory_facts import memory_facts_service


class TestSeedMemories:
    """测试 seed memories 创建功能"""

    def test_create_seed_memories_writes_to_table(self, db_session: Session):
        """验证 seed memories 写入 memory_facts 表"""
        # Setup: 创建测试数据
        user_id = 1
        world = World(id=1, user_id=user_id, name="TestWorld")
        db_session.add(world)
        db_session.commit()

        # Sage character (AI 老师)
        sage = Character(
            id=1,
            user_id=user_id,
            world_id=world.id,
            name="SageMaster",
            type="sage",
        )
        db_session.add(sage)

        # Traveler character (学生)
        traveler = Character(
            id=2,
            user_id=user_id,
            world_id=world.id,
            name="TestStudent",
            type="traveler",
            tags=["Python", "机器学习"],
            background="计算机专业大三学生",
            personality="好奇心强",
        )
        db_session.add(traveler)
        db_session.commit()

        # 执行: 创建 seed memories
        memory_ids = memory_facts_service.create_seed_memories(
            db=db_session,
            sage_character_id=sage.id,
            traveler_character=traveler,
            learner_profile=None,  # 暂不测试 learner_profile
        )

        # 验证: 写入数量
        assert len(memory_ids) >= 4, f"Expected at least 4 seed memories, got {len(memory_ids)}"

        # 验证: memory_facts 表有数据
        facts = db_session.query(MemoryFact).filter(
            MemoryFact.character_id == sage.id
        ).all()
        assert len(facts) >= 4, f"Expected at least 4 facts in table, got {len(facts)}"

        # 验证: 内容包含学生名字
        names = [f.content for f in facts if "TestStudent" in f.content]
        assert len(names) >= 1, "Seed memory should contain student name"

        # 验证: 内容包含学习方向
        tags = [f.content for f in facts if "Python" in f.content or "机器学习" in f.content]
        assert len(tags) >= 1, "Seed memory should contain learning tags"

        # 验证: 跨世界事实 (world_id = NULL)
        cross_world = [f for f in facts if f.world_id is None]
        assert len(cross_world) >= 4, "Seed memories should be cross-world (world_id=NULL)"

    def test_create_seed_memories_with_learner_profile(self, db_session: Session):
        """验证包含 learner_profile 数据的 seed memories"""
        # Setup
        user_id = 1
        world = World(id=1, user_id=user_id, name="TestWorld")
        db_session.add(world)

        sage = Character(id=1, user_id=user_id, world_id=world.id, name="SageMaster", type="sage")
        traveler = Character(id=2, user_id=user_id, world_id=world.id, name="Student2", type="traveler")
        db_session.add(sage)
        db_session.add(traveler)

        # LearnerProfile with learning stats
        profile = LearnerProfile(
            user_id=user_id,
            world_id=world.id,
            profile={
                "learning_stats": {
                    "total_sessions": 5,
                    "average_mastery": 0.72,
                },
                "preference_stability": {
                    "visual_examples": True,
                    "analogy_based": False,
                    "step_by_step": True,
                },
                "metacognition_trend": {
                    "planning": {"current": "中等", "trend": "上升"},
                },
            },
        )
        db_session.add(profile)
        db_session.commit()

        # 执行
        memory_ids = memory_facts_service.create_seed_memories(
            db=db_session,
            sage_character_id=sage.id,
            traveler_character=traveler,
            learner_profile=profile,
        )

        # 验证: 数量应该更多 (包含 profile 数据)
        facts = db_session.query(MemoryFact).filter(
            MemoryFact.character_id == sage.id
        ).all()
        
        # 基础: 4条 (name, tags, background, personality)
        # Profile: 约5条 (total_sessions, avg_mastery, 2 preferences, metacognition)
        assert len(facts) >= 6, f"Expected at least 6 facts with profile, got {len(facts)}"

        # 验证: 包含学习经历
        session_facts = [f for f in facts if "5 次学习经历" in f.content]
        assert len(session_facts) >= 1, "Should contain total_sessions memory"

        # 验证: 包含掌握度
        mastery_facts = [f for f in facts if "72%" in f.content]
        assert len(mastery_facts) >= 1, "Should contain average_mastery memory"

    def test_seed_memory_salience_values(self, db_session: Session):
        """验证 seed memories 使用正确的 salience 值"""
        user_id = 1
        world = World(id=1, user_id=user_id, name="TestWorld")
        db_session.add(world)

        sage = Character(id=1, user_id=user_id, world_id=world.id, name="Sage", type="sage")
        traveler = Character(id=2, user_id=user_id, world_id=world.id, name="Student", type="traveler")
        db_session.add(sage)
        db_session.add(traveler)
        db_session.commit()

        memory_facts_service.create_seed_memories(
            db=db_session,
            sage_character_id=sage.id,
            traveler_character=traveler,
            learner_profile=None,
        )

        facts = db_session.query(MemoryFact).all()

        # 验证 salience 范围
        for fact in facts:
            assert 0 <= fact.salience <= 1, f"Salience should be 0-1, got {fact.salience}"

        # 学生名字应该有高 salience (0.9)
        name_fact = next((f for f in facts if "Student" in f.content), None)
        if name_fact:
            assert name_fact.salience == 0.9, f"Name fact should have salience 0.9, got {name_fact.salience}"
