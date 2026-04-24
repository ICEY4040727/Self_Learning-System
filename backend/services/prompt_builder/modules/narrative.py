"""Narrative Module

历险叙事上下文注入模块。
从 World.scenes 中读取叙事配置（用户自定义或 AI 生成的世界背景），
注入 system prompt，让 Sage 在对话中自然呼应叙事框架。

固定层：始终注入，优先级 10（仅次于 WorldSetting）。
"""

from backend.services.prompt_builder.base import MemoryModule


class NarrativeModule(MemoryModule):
    """叙事上下文模块

    从 World.scenes 的 narrative 字段读取叙事配置：
    - world_theme: 世界主题（如"赛博朋克黑客城市"）
    - learner_role: 学习者角色
    - sage_role: Sage 角色定位
    - knowledge_metaphor: 知识比喻映射
    - progression_arc: 成长主线
    - event_templates: 事件模板（此处不注入，由前端弹窗使用）

    叙事框架定义了"我们在哪、我们是谁"，始终注入以确保沉浸感。
    """

    always_include = True

    def get_section_name(self) -> str:
        return "【历险叙事】"

    def get_priority(self) -> int:
        return 10

    def should_include(self, context: dict) -> bool:
        """需要有 world_id 才能获取叙事信息"""
        return context.get("world_id") is not None

    def assemble(self, context: dict) -> str | None:
        """从 world.scenes 读取叙事配置并注入"""
        db = context.get("db")
        world_id = context.get("world_id")

        if not db or not world_id:
            return None

        from backend.models.models import World

        world = db.query(World).filter(World.id == world_id).first()
        if not world:
            return None

        scenes = world.scenes or {}
        narrative = scenes.get("narrative") or scenes.get("narrative_input")

        # 兼容两种结构：直接 narrative 或 narrative_input.ai_generated
        if narrative and "ai_generated" in narrative:
            narrative = narrative["ai_generated"]

        if not narrative or not isinstance(narrative, dict):
            # 没有叙事配置时不注入（不报错，静默降级）
            return None

        parts = []

        # 世界主题
        theme = narrative.get("world_theme")
        if theme:
            parts.append(f"当前历险世界：{theme}")

        # 角色定位
        learner_role = narrative.get("learner_role")
        if learner_role:
            parts.append(f"学习者扮演：{learner_role}")

        sage_role = narrative.get("sage_role")
        if sage_role:
            parts.append(f"你（Sage）扮演：{sage_role}")

        # 知识比喻
        metaphor = narrative.get("knowledge_metaphor")
        if metaphor:
            parts.append(f"知识比喻：{metaphor}。请在教学中自然地使用这种比喻来解释概念。")

        # 成长主线
        arc = narrative.get("progression_arc")
        if arc:
            parts.append(f"成长主线：{arc}")

        # 叙事引导
        if parts:
            parts.append(
                "请将以上叙事设定融入你的教学对话中，保持沉浸感。"
                "不要打破第四面墙，始终以 Sage 角色身份发言。"
            )

        return "\n".join(parts) if parts else None