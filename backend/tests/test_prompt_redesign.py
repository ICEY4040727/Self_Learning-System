"""Tests for Phase 3 Step 1: Prompt 组装策略重设计

验证：
1. always_include 类属性存在且工作
2. 固定层模块（WorldSetting, Narrative）始终注入
3. 动态层模块按 should_include 条件注入
4. 模块按 priority 排序
5. NarrativeModule 读取叙事配置
6. 全量回归（Phase 2 测试不受影响）
"""

import pytest

from backend.services.prompt_builder.base import MemoryModule
from backend.services.prompt_builder.builder import PromptBuilder, SceneConfig
from backend.services.prompt_builder.modules.narrative import NarrativeModule
from backend.services.prompt_builder.modules.world_setting import WorldSettingModule


# ─── 1. always_include 类属性 ───


class TestAlwaysInclude:
    """验证 always_include 机制"""

    def test_base_class_default_false(self):
        """MemoryModule 基类默认 always_include=False"""
        assert MemoryModule.always_include is False

    def test_world_setting_always_include(self):
        """WorldSettingModule 设置了 always_include=True"""
        assert WorldSettingModule.always_include is True

    def test_narrative_always_include(self):
        """NarrativeModule 设置了 always_include=True"""
        assert NarrativeModule.always_include is True


# ─── 2. 固定层模块始终注入 ───


class TestFixedLayerModules:
    """验证固定层模块在 build_dynamic_layer 中始终注入"""

    def test_world_setting_included_without_should(self):
        """WorldSettingModule 即使 should_include 返回 False，
        但因 always_include=True，仍会被注入（assemble 有内容时）"""
        module = WorldSettingModule()
        # should_include 无 world_id 时返回 False
        context = {"world_id": None, "db": None}
        assert module.should_include(context) is False
        # 但 always_include=True
        assert module.always_include is True
        # 实际注入判断: always_include OR should_include
        # 无 db 时 assemble 返回空字符串（falsy），不会出现在结果中
        assert module.assemble(context) == ""

    def test_narrative_no_config_graceful(self):
        """NarrativeModule 在没有叙事配置时优雅降级"""
        module = NarrativeModule()
        # 无 world 的 context
        context = {"world_id": None, "db": None}
        assert module.assemble(context) is None


# ─── 3. 模块按 priority 排序 ───


class TestPrioritySorting:
    """验证模块按 priority 排序"""

    def test_module_configs_has_priority_order(self):
        """LEARNING 场景的模块列表包含固定层模块"""
        modules = SceneConfig.get_modules("learning")
        module_classes = [m for m in modules]
        assert WorldSettingModule in module_classes
        assert NarrativeModule in module_classes

    def test_priority_values(self):
        """各模块 priority 值正确"""
        module = WorldSettingModule()
        assert module.get_priority() == 5

        module = NarrativeModule()
        assert module.get_priority() == 10


# ─── 4. NarrativeModule 组装 ───


class TestNarrativeModuleAssemble:
    """验证 NarrativeModule 从 Course.meta 读取叙事配置"""

    def test_assemble_with_narrative_config(self, db_session):
        """有叙事配置时正确注入"""
        from backend.models.models import Course, World

        world = World(
            user_id=1,
            name="赛博之城",
            description="测试世界",
        )
        db_session.add(world)
        db_session.commit()

        course = Course(
            world_id=world.id,
            name="赛博课程",
            meta={
                "course_narrative_plan": {
                    "world": {"name": "赛博之城"},
                    "route_bible": {"main_arc": "从街头混混到传说级黑客"},
                    "narrative_input": {
                        "world_theme": "赛博朋克黑客城市",
                        "learner_role": "新晋黑客",
                        "sage_role": "传奇黑客导师",
                        "knowledge_metaphor": "编程概念=黑客技能",
                        "progression_arc": "从街头混混到传说级黑客",
                    },
                }
            },
        )
        db_session.add(course)
        db_session.commit()

        module = NarrativeModule()
        context = {"db": db_session, "course_id": course.id}
        result = module.assemble(context)

        assert result is not None
        assert "赛博朋克黑客城市" in result
        assert "新晋黑客" in result
        assert "传奇黑客导师" in result
        assert "编程概念=黑客技能" in result
        assert "从街头混混到传说级黑客" in result
        assert "沉浸感" in result

    def test_assemble_with_ai_generated_wrapper(self, db_session):
        """兼容 narrative_input.ai_generated 结构"""
        from backend.models.models import Course, World

        world = World(
            user_id=1,
            name="魔法学院",
            description="",
        )
        db_session.add(world)
        db_session.commit()

        course = Course(
            world_id=world.id,
            name="魔法课程",
            meta={
                "course_narrative_plan": {
                    "narrative_input": {
                        "mode": "prompt",
                        "user_prompt": "我想在魔法学院学魔法",
                        "ai_generated": {
                            "world_theme": "魔法学院",
                            "learner_role": "新生",
                            "sage_role": "大法师",
                            "knowledge_metaphor": "知识=魔法",
                            "progression_arc": "从学徒到大法师",
                        },
                    }
                }
            },
        )
        db_session.add(course)
        db_session.commit()

        module = NarrativeModule()
        context = {"db": db_session, "course_id": course.id}
        result = module.assemble(context)

        assert result is not None
        assert "魔法学院" in result
        assert "大法师" in result

    def test_assemble_no_narrative(self, db_session):
        """无叙事配置时返回 None"""
        from backend.models.models import Course, World

        world = World(user_id=1, name="空白世界", description="")
        db_session.add(world)
        db_session.commit()

        course = Course(world_id=world.id, name="空白课程", meta={})
        db_session.add(course)
        db_session.commit()

        module = NarrativeModule()
        context = {"db": db_session, "course_id": course.id}
        result = module.assemble(context)

        assert result is None

    def test_assemble_ignores_legacy_world_plan_key(self, db_session):
        """只写旧 world_plan 时不再注入课程叙事"""
        from backend.models.models import Course, World

        world = World(user_id=1, name="旧结构世界", description="测试")
        db_session.add(world)
        db_session.commit()

        course = Course(
            world_id=world.id,
            name="旧结构课程",
            meta={
                "world_plan": {
                    "narrative_input": {
                        "world_theme": "不应再被读取",
                    }
                }
            },
        )
        db_session.add(course)
        db_session.commit()

        module = NarrativeModule()
        context = {"db": db_session, "course_id": course.id}
        result = module.assemble(context)

        assert result is None


# ─── 5. 集成测试：PromptBuilder 完整组装 ───


class TestPromptBuilderIntegration:
    """验证 PromptBuilder 完整组装包含固定层"""

    def test_dynamic_layer_includes_fixed_modules(self, db_session):
        """build_dynamic_layer 包含固定层模块"""
        from backend.models.models import Course, World

        world = World(
            user_id=1,
            name="测试世界",
            description="一个测试世界",
        )
        db_session.add(world)
        db_session.commit()

        course = Course(
            world_id=world.id,
            name="测试课程",
            meta={
                "course_narrative_plan": {
                    "narrative_input": {
                        "world_theme": "测试世界主题",
                        "sage_role": "测试导师",
                    }
                }
            },
        )
        db_session.add(course)
        db_session.commit()

        builder = PromptBuilder(db=db_session)
        context = {
            "db": db_session,
            "world_id": world.id,
            "course_id": course.id,
            "session_id": 1,
            "learner_profile": None,
            "prev_emotion": None,
            "mastery_level": 50,
            "user_message": "测试",
            "relationship": {},
        }

        result = builder.build_dynamic_layer("learning", context)

        # 固定层模块应出现在结果中
        assert "【当前世界】" in result
        assert "【历险叙事】" in result
        assert "测试世界主题" in result

    def test_full_build_structure(self, db_session):
        """完整 build 包含静态层和动态层"""
        from backend.models.models import Character, Course, World, WorldCharacter

        char = Character(
            user_id=1,
            name="测试Sage",
            background="一个测试角色",
        )
        db_session.add(char)
        db_session.commit()

        world = World(
            user_id=1,
            name="完整测试世界",
            description="测试",
        )
        db_session.add(world)
        db_session.commit()

        course = Course(
            world_id=world.id,
            name="完整测试课程",
            meta={
                "course_narrative_plan": {
                    "narrative_input": {
                        "world_theme": "完整测试主题",
                    }
                }
            },
        )
        db_session.add(course)
        db_session.commit()

        db_session.add(WorldCharacter(
            world_id=world.id,
            character_id=char.id,
            role="sage",
            is_primary=True,
            world_title="世界导师",
            world_background="这个世界中的测试背景",
            relationship_seed="在图书馆门口第一次见面",
            world_greeting="欢迎来到这个世界，我们从整体开始。",
        ))
        db_session.commit()

        builder = PromptBuilder(db=db_session)
        context = {
            "db": db_session,
            "world_id": world.id,
            "course_id": course.id,
            "session_id": 1,
            "learner_profile": None,
            "prev_emotion": None,
            "mastery_level": 50,
            "user_message": "测试",
            "relationship": {},
        }

        result = builder.build(character=char, scene="learning", context=context)

        # 静态层
        assert "测试Sage" in result
        assert "这个世界中的测试背景" in result
        assert "在图书馆门口第一次见面" in result
        assert "一个测试角色" not in result
        assert "苏格拉底" in result
        # 动态层
        assert "【当前世界】" in result
        assert "完整测试世界" in result
        # 分隔符
        assert "---" in result
