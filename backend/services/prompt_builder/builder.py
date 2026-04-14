"""Prompt Builder
模块化提示词构建器

P1 #183 存储结构重设计:
- 移除 KnowledgeModule（使用 memory_facts 表）
- 移除 MemoryRetrievalModule（使用 MemoryFactsModule）
- 添加 MemoryFactsModule（从 memory_facts 检索记忆）
"""

import logging
from typing import TYPE_CHECKING, Any

from backend.services.prompt_builder.base import ContextProvider, MemoryModule
from backend.services.prompt_builder.contexts.relationship import RelationshipContext
from backend.services.prompt_builder.contexts.scaffold import ScaffoldContext
from backend.services.prompt_builder.modules.affect import AffectModule
from backend.services.prompt_builder.modules.episode import EpisodeModule
from backend.services.prompt_builder.modules.memory_facts import MemoryFactsModule
from backend.services.prompt_builder.modules.metacognition import MetacognitionModule
from backend.services.prompt_builder.modules.misconception import MisconceptionModule
from backend.services.prompt_builder.modules.preference import PreferenceModule

if TYPE_CHECKING:
    from backend.models.models import Character

logger = logging.getLogger(__name__)


class SceneConfig:
    """场景配置"""

    LEARNING = "learning"
    REVIEW = "review"
    ASSESSMENT = "assessment"

    # 场景配置：定义每个场景使用的模块
    # 优先级顺序：Misconception(30) → Episode(40) → Preference(50) → Affect(60) → MemoryFacts(70) → Metacognition(80)
    MODULE_CONFIGS = {
        LEARNING: [
            MisconceptionModule,
            EpisodeModule,
            PreferenceModule,
            AffectModule,
            MemoryFactsModule,
            MetacognitionModule,
        ],
        REVIEW: [
            MemoryFactsModule,
        ],
        ASSESSMENT: [
            # 评估场景暂不添加特定模块
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
        db=None,
        relationship_svc=None,
    ):
        # Phase 1.5 DD12: knowledge_svc 重命名为 db
        self.db = db
        self.relationship = relationship_svc

    def _get_character(self, character_or_id, db=None) -> "Character | None":
        """从 character 对象或 ID 获取 Character 模型"""
        from backend.models.models import Character

        if character_or_id is None:
            return None

        # 如果传入的是整数 ID
        if isinstance(character_or_id, int):
            target_db = db or self.db
            if target_db is not None:
                return target_db.query(Character).filter(Character.id == character_or_id).first()
            return None

        # 如果传入的是 Character 对象
        if isinstance(character_or_id, Character):
            return character_or_id

        # 如果传入的是 TeacherPersona 对象（兼容旧代码）
        from backend.models.models import TeacherPersona
        if isinstance(character_or_id, TeacherPersona):
            character_id = getattr(character_or_id, 'character_id', None)
            if character_id:
                target_db = db or self.db
                if target_db is not None:
                    return target_db.query(Character).filter(Character.id == character_id).first()
            return None

        return None

    def build_static_layer(
        self,
        character,
        traveler_character=None,
        db=None,
    ) -> str:
        """构建静态层

        Phase 1.5 DD1: 参数从 teacher_persona 改为 character

        静态层包含不随对话变化的内容：
        - Teacher Persona（从 Character 表注入信息）
        - Socratic Method Rules
        - Mermaid Rules
        - Traveler 角色信息（可选）
        """
        parts = []

        # 1. Teacher Persona - 从 Character 获取信息
        char = self._get_character(character, db)

        if char:
            # 角色身份（必填）
            parts.append(f"你是 {char.name}")

            # 注入 background（角色背景故事）
            background = getattr(char, 'background', None)
            if background:
                parts.append(background)

            # 注入 personality（性格特点）
            personality = getattr(char, 'personality', None)
            if personality:
                parts.append(f"性格特点: {personality}")

            # 注入 speech_style（说话风格）
            speech_style = getattr(char, 'speech_style', None)
            if speech_style:
                parts.append(f"说话风格: {speech_style}")

            # 注入 tags（特质）
            tags = getattr(char, 'tags', None)
            if tags and isinstance(tags, (list, tuple)):
                parts.append(f"角色特质: {', '.join(str(t) for t in tags)}")

            # 注入 traits（性格参数，Phase 1.5 DD1）
            # Phase 1.5: 从 Character.traits 读取，格式: {"strictness": 5, "pace": 5, "questioning": 5, "warmth": 5, "humor": 5}
            traits = getattr(char, 'traits', None)
            if traits and isinstance(traits, dict) and traits:
                parts.append(
                    f"【性格参数 0-10】严厉度={traits.get('strictness', 5)}, "
                    f"节奏={traits.get('pace', 5)}, 提问倾向={traits.get('questioning', 5)}, "
                    f"温度={traits.get('warmth', 5)}, 幽默={traits.get('humor', 5)}。"
                    "请让你的回应风格严格符合上述参数。"
                )

            # 注入 system_prompt_template（自定义模板）
            system_prompt_template = getattr(char, 'system_prompt_template', None)
            if system_prompt_template:
                parts.append(system_prompt_template)
        else:
            # 降级方案
            parts.append(
                "你是一位富有耐心的教师，"
                "运用苏格拉底教学法帮助学生自主思考和探索知识。"
            )

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
            tags = getattr(traveler_character, "tags", None)
            if tags and isinstance(tags, (list, tuple)):
                parts.append(f"学习风格: {', '.join(str(t) for t in tags)}")

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
        character,
        scene: str,
        context: dict[str, Any],
        traveler_character=None,
    ) -> str:
        """构建完整系统提示词

        Phase 1.5 DD1: 参数从 teacher_persona 改为 character
        合并静态层和动态层。
        """
        # 从 context 中获取 db session
        db = context.get("db")
        static = self.build_static_layer(character, traveler_character, db)
        dynamic = self.build_with_fallback(scene, context)
        return f"{static}\n\n---\n\n{dynamic}"


# 全局实例
prompt_builder = PromptBuilder()
