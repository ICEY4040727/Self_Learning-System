"""Tests for Prompt Builder Module
模块化提示词注入器的单元测试
"""

from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from backend.services.prompt_builder import (
    PromptBuilder,
    SceneConfig,
)
from backend.services.prompt_builder.contexts.relationship import RelationshipContext
from backend.services.prompt_builder.contexts.scaffold import ScaffoldContext
from backend.services.prompt_builder.modules.affect import AffectModule
from backend.services.prompt_builder.modules.knowledge import KnowledgeModule
from backend.services.prompt_builder.modules.metacognition import MetacognitionModule
from backend.services.prompt_builder.modules.preference import PreferenceModule


class TestSceneConfig:
    """SceneConfig 测试"""

    def test_scene_constants(self):
        """测试场景常量定义"""
        assert SceneConfig.LEARNING == "learning"
        assert SceneConfig.REVIEW == "review"
        assert SceneConfig.ASSESSMENT == "assessment"

    def test_get_modules_learning(self):
        """测试 LEARNING 场景的模块列表"""
        modules = SceneConfig.get_modules(SceneConfig.LEARNING)
        assert KnowledgeModule in modules
        assert PreferenceModule in modules

    def test_get_modules_review(self):
        """测试 REVIEW 场景的模块列表"""
        modules = SceneConfig.get_modules(SceneConfig.REVIEW)
        assert KnowledgeModule in modules
        assert len(modules) == 1

    def test_get_contexts(self):
        """测试上下文提供者列表"""
        contexts = SceneConfig.get_contexts(SceneConfig.LEARNING)
        assert RelationshipContext in contexts
        assert ScaffoldContext in contexts


class TestRelationshipContext:
    """RelationshipContext 测试"""

    def test_priority(self):
        """测试优先级"""
        ctx = RelationshipContext()
        assert ctx.get_priority() == 1

    def test_should_include(self):
        """测试 should_include"""
        ctx = RelationshipContext()
        assert ctx.should_include({}) is True

    def test_assemble_stranger(self):
        """测试 stranger 阶段"""
        ctx = RelationshipContext()
        result = ctx.assemble({"relationship": {"stage": "stranger"}})
        assert "stranger" in result
        assert "温和、耐心" in result

    def test_assemble_friend(self):
        """测试 friend 阶段"""
        ctx = RelationshipContext()
        result = ctx.assemble({"relationship": {"stage": "friend"}})
        assert "friend" in result
        assert "朋友" in result

    def test_assemble_with_dimensions(self):
        """测试带维度的组装"""
        ctx = RelationshipContext()
        result = ctx.assemble({
            "relationship": {
                "stage": "mentor",
                "dimensions": {"trust": 0.8, "familiarity": 0.6}
            }
        })
        assert "mentor" in result
        assert "trust: 0.80" in result


class TestScaffoldContext:
    """ScaffoldContext 测试"""

    def test_priority(self):
        """测试优先级"""
        ctx = ScaffoldContext()
        assert ctx.get_priority() == 2

    def test_should_include(self):
        """测试 should_include"""
        ctx = ScaffoldContext()
        assert ctx.should_include({}) is True

    def test_compute_scaffold_level_frustration(self):
        """测试 frustration 情感"""
        assert ScaffoldContext.compute_scaffold_level("frustration", 20) == 5
        assert ScaffoldContext.compute_scaffold_level("frustration", 50) == 4

    def test_compute_scaffold_level_confusion(self):
        """测试 confusion 情感"""
        assert ScaffoldContext.compute_scaffold_level("confusion", 30) == 4
        assert ScaffoldContext.compute_scaffold_level("confusion", 70) == 3

    def test_compute_scaffold_level_curiosity(self):
        """测试 curiosity 情感"""
        assert ScaffoldContext.compute_scaffold_level("curiosity", 50) == 3
        assert ScaffoldContext.compute_scaffold_level("curiosity", 80) == 2

    def test_compute_scaffold_level_neutral(self):
        """测试 neutral 情感"""
        assert ScaffoldContext.compute_scaffold_level("neutral", 80) == 2
        assert ScaffoldContext.compute_scaffold_level("neutral", 50) == 3
        assert ScaffoldContext.compute_scaffold_level("neutral", 20) == 4

    def test_assemble(self):
        """测试组装"""
        ctx = ScaffoldContext()
        result = ctx.assemble({
            "prev_emotion": {"emotion_type": "curiosity"},
            "mastery_level": 60
        })
        assert "curiosity" in result
        assert "60" in result
        assert "脚手架" in result


class TestKnowledgeModule:
    """KnowledgeModule 测试"""

    def test_section_name(self):
        """测试模块名称"""
        module = KnowledgeModule()
        assert module.get_section_name() == "【当前知识状态】"

    def test_priority(self):
        """测试优先级"""
        module = KnowledgeModule()
        assert module.get_priority() == 10

    def test_should_include(self):
        """测试 should_include"""
        module = KnowledgeModule()
        assert module.should_include({}) is True

    def test_assemble_no_context(self):
        """测试无上下文"""
        module = KnowledgeModule()
        result = module.assemble({})
        assert result is None

    def test_assemble_no_db(self):
        """测试无数据库"""
        module = KnowledgeModule()
        result = module.assemble({"world_id": 1})
        assert result is None

    @patch("backend.services.prompt_builder.modules.knowledge.knowledge_service")
    def test_assemble_with_data(self, mock_service):
        """测试有数据的组装"""
        mock_service.get_knowledge.return_value = {
            "concepts": {
                "recursion": {"name": "递归", "mastery": 0.9},
                "loop": {"name": "循环", "mastery": 0.5},
                "function": {"name": "函数", "mastery": 0.2},
            }
        }

        module = KnowledgeModule()
        result = module.assemble({"db": MagicMock(), "world_id": 1})

        assert result is not None
        assert "已掌握" in result
        assert "学习中" in result
        assert "初识" in result
        assert "递归" in result


class TestPreferenceModule:
    """PreferenceModule 测试"""

    def test_section_name(self):
        """测试模块名称"""
        module = PreferenceModule()
        assert module.get_section_name() == "【学习偏好】"

    def test_priority(self):
        """测试优先级"""
        module = PreferenceModule()
        assert module.get_priority() == 50

    def test_should_include_no_profile(self):
        """测试无 profile"""
        module = PreferenceModule()
        assert module.should_include({}) is False

    def test_should_include_with_profile(self):
        """测试有 profile"""
        module = PreferenceModule()
        profile = SimpleNamespace(profile={})
        assert module.should_include({"learner_profile": profile}) is True

    def test_assemble_with_preferences(self):
        """测试有偏好的组装"""
        module = PreferenceModule()
        profile = SimpleNamespace(profile={
            "preferences": {
                "visual_examples": {"value": True, "confidence": 0.9},
                "pace": {"value": "slow"},
            }
        })
        result = module.assemble({"learner_profile": profile})

        assert result is not None
        assert "visual_examples" in result
        assert "True" in result
        assert "slow" in result


class TestMetacognitionModule:
    """MetacognitionModule 测试"""

    def test_section_name(self):
        """测试模块名称"""
        module = MetacognitionModule()
        assert module.get_section_name() == "【元认知】"

    def test_priority(self):
        """测试优先级"""
        module = MetacognitionModule()
        assert module.get_priority() == 70

    def test_assemble_with_metacognition(self):
        """测试有元认知的组装"""
        module = MetacognitionModule()
        profile = SimpleNamespace(profile={
            "metacognition": {
                "planning": {"value": "high"},
                "monitoring": {"value": "medium"},
            }
        })
        result = module.assemble({"learner_profile": profile})

        assert result is not None
        assert "planning" in result
        assert "high" in result


class TestAffectModule:
    """AffectModule 测试"""

    def test_section_name(self):
        """测试模块名称"""
        module = AffectModule()
        assert module.get_section_name() == "【情感模式】"

    def test_priority(self):
        """测试优先级"""
        module = AffectModule()
        assert module.get_priority() == 60

    def test_assemble_with_affect(self):
        """测试有情感模式的组装"""
        module = AffectModule()
        profile = SimpleNamespace(profile={
            "affect": {
                "frustration_tolerance": {"value": "low"},
            }
        })
        result = module.assemble({"learner_profile": profile})

        assert result is not None
        assert "frustration_tolerance" in result
        assert "low" in result


class TestPromptBuilder:
    """PromptBuilder 测试"""

    def test_build_static_layer_basic(self):
        """测试静态层基本构建"""
        builder = PromptBuilder()
        persona = SimpleNamespace(
            name="苏格拉底",
            system_prompt_template="你是一位哲学家"
        )
        result = builder.build_static_layer(persona)

        assert "哲学家" in result
        assert "苏格拉底式提问" in result
        assert "Mermaid" in result

    def test_build_static_layer_with_traveler(self):
        """测试带 Traveler 的静态层"""
        builder = PromptBuilder()
        persona = SimpleNamespace(name="老师", system_prompt_template="")
        traveler = SimpleNamespace(
            name="学生A",
            background="热爱数学",
            personality="好奇"
        )
        result = builder.build_static_layer(persona, traveler_character=traveler)

        assert "学生A" in result
        assert "热爱数学" in result
        assert "好奇" in result

    def test_build_dynamic_layer_basic(self):
        """测试动态层基本构建"""
        builder = PromptBuilder()
        context = {
            "relationship": {"stage": "friend"},
            "prev_emotion": {"emotion_type": "curiosity"},
            "mastery_level": 60,
        }
        result = builder.build_dynamic_layer(SceneConfig.LEARNING, context)

        assert "friend" in result
        assert "curiosity" in result

    def test_build_with_fallback(self):
        """测试带降级的构建"""
        builder = PromptBuilder()
        context = {"invalid": "context"}
        result = builder.build_with_fallback(SceneConfig.LEARNING, context)

        assert result is not None
        assert "stranger" in result  # 降级版本

    def test_build_full(self):
        """测试完整构建"""
        builder = PromptBuilder()
        persona = SimpleNamespace(name="老师", system_prompt_template="")
        context = {
            "relationship": {"stage": "stranger"},
            "prev_emotion": {"emotion_type": "neutral"},
            "mastery_level": 50,
        }
        result = builder.build(persona, SceneConfig.LEARNING, context)

        assert "老师" in result
        assert "苏格拉底式提问" in result
        assert "stranger" in result
        assert "---" in result
