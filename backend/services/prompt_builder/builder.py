"""Prompt Builder
模块化提示词构建器
"""

import logging
from typing import Any

from backend.services.prompt_builder.base import ContextProvider, MemoryModule
from backend.services.prompt_builder.contexts.relationship import RelationshipContext
from backend.services.prompt_builder.contexts.scaffold import ScaffoldContext
from backend.services.prompt_builder.modules.affect import AffectModule
from backend.services.prompt_builder.modules.episode import EpisodeModule
from backend.services.prompt_builder.modules.knowledge import KnowledgeModule
from backend.services.prompt_builder.modules.memory_retrieval import MemoryRetrievalModule
from backend.services.prompt_builder.modules.metacognition import MetacognitionModule
from backend.services.prompt_builder.modules.misconception import MisconceptionModule
from backend.services.prompt_builder.modules.preference import PreferenceModule

logger = logging.getLogger(__name__)


class SceneConfig:
    """场景配置"""
    
    LEARNING = "learning"
    REVIEW = "review"
    ASSESSMENT = "assessment"
    
    # 场景配置：定义每个场景使用的模块
    # 优先级顺序：Knowledge(10) → Misconception(30) → Episode(40) → Preference(50) → Affect(60) → Metacognition(70) → MemoryRetrieval(80)
    MODULE_CONFIGS = {
        LEARNING: [
            KnowledgeModule,
            MisconceptionModule,
            EpisodeModule,
            PreferenceModule,
            AffectModule,
            MetacognitionModule,
            MemoryRetrievalModule,
        ],
        REVIEW: [
            KnowledgeModule,
            MemoryRetrievalModule,
        ],
        ASSESSMENT: [
            KnowledgeModule,
        ],
    }
    
    # 上下文提供者（所有场景通用）
    CONTEXT_PROVIDERS = [
        RelationshipContext,
        ScaffoldContext,
    ]
    
    @classmethod
    def get_modules(cls, scene: str) -> list[type[MemoryModule]]:
        """获取场景对应的模块列表"""
        return cls.MODULE_CONFIGS.get(scene, cls.MODULE_CONFIGS[cls.LEARNING])
    
    @classmethod
    def get_contexts(cls, scene: str) -> list[type[ContextProvider]]:
        """获取场景对应的上下文提供者列表"""
        return cls.CONTEXT_PROVIDERS


class PromptBuilder:
    """提示词构建器
    
    将提示词构建过程模块化，支持：
    - 静态层：教师人格 + 苏格拉底方法 + Mermaid
    - 动态层：关系阶段 + 脚手架 + 记忆模块
    """
    
    def __init__(
        self,
        knowledge_svc=None,
        relationship_svc=None,
    ):
        self.knowledge = knowledge_svc
        self.relationship = relationship_svc
    
    def build_static_layer(
        self,
        teacher_persona,
        traveler_character=None,
    ) -> str:
        """构建静态层
        
        静态层包含不随对话变化的内容：
        - Teacher Persona
        - Socratic Method Rules
        - Mermaid Rules
        - Traveler 角色信息（可选）
        """
        parts = []
        
        # 1. Teacher Persona
        persona = getattr(teacher_persona, "system_prompt_template", None) or ""
        if not persona:
            name = getattr(teacher_persona, "name", "老师")
            persona = (
                f"你是 {name}，一位富有耐心的教师，"
                f"运用苏格拉底教学法帮助学生自主思考和探索知识。"
            )
        parts.append(persona)
        
        # 2. Socratic Method Rules
        parts.append("""【教学方法——苏格拉底式提问】
1. 绝不直接给出答案。通过一连串由浅入深的问题引导学习者自己发现答案。
2. 每次回复至少包含一个引导性问题，推动学习者思考下一步。
3. 当学习者的回答有误时，不要直接纠正；而是通过反问让他们重新审视自己的推理。
4. 适时总结学习者已经掌握的部分，再引向尚未理解的部分。
5. 保持专业、耐心、鼓励的态度。""")
        
        # 3. Mermaid Rules
        parts.append("""【可视化工具——Mermaid 图表】
当概念关系、流程步骤、知识结构需要可视化时，可以在回复中使用 ```mermaid 代码块生成图表。
支持的图表类型：flowchart（流程图）、mindmap（思维导图）、sequenceDiagram（时序图）、classDiagram（类图）、graph（关系图）。
使用时机：解释复杂概念关系、展示解题步骤、梳理知识结构时。不要每次回复都画图，只在图表确实有助于理解时使用。""")
        
        # 4. Traveler 角色信息（可选）
        if traveler_character:
            name = getattr(traveler_character, "name", "学习者")
            parts.append(f"""【学习者身份】
用户扮演的角色是 "{name}"。""")
            background = getattr(traveler_character, "background", None)
            if background:
                parts.append(f"角色背景: {background}")
            personality = getattr(traveler_character, "personality", None)
            if personality:
                parts.append(f"角色特点: {personality}")
        
        return "\n\n".join(parts)
    
    def build_dynamic_layer(
        self,
        scene: str,
        context: dict[str, Any],
    ) -> str:
        """构建动态层
        
        动态层包含随对话变化的内容，按优先级排序。
        
        Args:
            scene: 场景类型（LEARNING/REVIEW/ASSESSMENT）
            context: 上下文字典，包含:
                - db: Session
                - world_id: int
                - session_id: int
                - relationship: dict
                - learner_profile: LearnerProfile | None
                - prev_emotion: dict | None
                - mastery_level: int
                - user_message: str
                - checkpoint_time: str | None
                - knowledge_context: str
        """
        parts = []
        
        # 1. ContextProviders（关系、脚手架）
        for ctx_class in SceneConfig.get_contexts(scene):
            ctx = ctx_class()
            if ctx.should_include(context):
                try:
                    content = ctx.assemble(context)
                    if content:
                        parts.append(content)
                except Exception as e:
                    logger.warning(f"ContextProvider {ctx_class.__name__} failed: {e}")
        
        # 2. MemoryModules（按 priority 排序）
        for module_class in SceneConfig.get_modules(scene):
            module = module_class()
            if module.should_include(context):
                try:
                    content = module.assemble(context)
                    if content:
                        parts.append(f"{module.get_section_name()}\n{content}")
                except Exception as e:
                    logger.warning(f"MemoryModule {module_class.__name__} failed: {e}")
        
        # 3. Knowledge Context（图谱）
        knowledge_context = context.get("knowledge_context")
        if knowledge_context:
            parts.append("【学习者已掌握的知识关系】\n" + knowledge_context)
        
        return "\n\n".join(parts)
    
    def build_with_fallback(
        self,
        scene: str,
        context: dict[str, Any],
    ) -> str:
        """带降级的构建
        
        如果构建失败，降级到基础版本。
        """
        try:
            return self.build_dynamic_layer(scene, context)
        except Exception as e:
            logger.warning(f"PromptBuilder.build_dynamic_layer failed: {e}, falling back to basic")
            return self._build_basic_dynamic_layer(context)
    
    def _build_basic_dynamic_layer(self, context: dict[str, Any]) -> str:
        """降级版本 - 简单的动态层
        
        当模块化构建失败时使用。
        """
        parts = []
        
        relationship = context.get("relationship", {})
        stage = relationship.get("stage", "stranger")
        parts.append(f"【当前关系阶段：{stage}】")
        
        emotion = context.get("prev_emotion", {})
        mastery = context.get("mastery_level", 50)
        emotion_type = emotion.get("emotion_type", "neutral")
        parts.append(f"【学习者状态】情感: {emotion_type} | 知识掌握度: {mastery}/100")
        
        return "\n\n".join(parts)
    
    def build(
        self,
        teacher_persona,
        scene: str,
        context: dict[str, Any],
        traveler_character=None,
    ) -> str:
        """构建完整系统提示词
        
        合并静态层和动态层。
        """
        static = self.build_static_layer(teacher_persona, traveler_character)
        dynamic = self.build_with_fallback(scene, context)
        return f"{static}\n\n---\n\n{dynamic}"


# 全局实例
prompt_builder = PromptBuilder()
