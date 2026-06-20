"""Narrative Module

课程叙事上下文注入模块。
从 Course.meta 中读取课程叙事结构，
注入 system prompt，让 Sage 在对话中自然呼应课程叙事框架。

固定层：始终注入，优先级 10（仅次于 WorldSetting）。
"""

from backend.services.prompt_builder.base import MemoryModule


class NarrativeModule(MemoryModule):
    """课程叙事上下文模块

    从 Course.meta.course_narrative_plan 读取叙事配置。
    """

    always_include = True

    def get_section_name(self) -> str:
        return "【历险叙事】"

    def get_priority(self) -> int:
        return 10

    def should_include(self, context: dict) -> bool:
        """需要有 course_id 才能获取叙事信息"""
        return context.get("course_id") is not None

    def assemble(self, context: dict) -> str | None:
        """从课程 meta 读取叙事配置并注入"""
        db = context.get("db")
        course_id = context.get("course_id")

        if not db or not course_id:
            return None

        from backend.models.models import Course

        course = db.query(Course).filter(Course.id == course_id).first()
        if not course:
            return None

        meta = course.meta or {}
        narrative = meta.get("course_narrative_plan")
        if not narrative or not isinstance(narrative, dict):
            return None

        world_section = narrative.get("world") if isinstance(narrative.get("world"), dict) else {}
        route_bible = narrative.get("route_bible") if isinstance(narrative.get("route_bible"), dict) else {}

        generated = narrative.get("ai_generated")
        if isinstance(generated, dict):
            narrative_input = generated
        else:
            narrative_input = narrative.get("narrative_input")
            if isinstance(narrative_input, dict) and isinstance(narrative_input.get("ai_generated"), dict):
                narrative_input = narrative_input["ai_generated"]

        if not isinstance(narrative_input, dict):
            narrative_input = {}

        parts = []

        theme = narrative_input.get("world_theme") or world_section.get("name")
        if theme:
            parts.append(f"当前历险世界：{theme}")

        learner_role = narrative_input.get("learner_role")
        if learner_role:
            parts.append(f"学习者扮演：{learner_role}")

        sage_role = narrative_input.get("sage_role")
        if sage_role:
            parts.append(f"你（Sage）扮演：{sage_role}")

        metaphor = narrative_input.get("knowledge_metaphor")
        if metaphor:
            parts.append(f"知识比喻：{metaphor}。请在教学中自然地使用这种比喻来解释概念。")

        arc = narrative_input.get("progression_arc") or route_bible.get("main_arc")
        if arc:
            parts.append(f"成长主线：{arc}")

        boundaries = route_bible.get("boundaries")
        if boundaries and isinstance(boundaries, list):
            parts.append("叙事边界：" + "；".join(str(item) for item in boundaries if item))

        if parts:
            parts.append(
                "请将以上叙事设定融入你的教学对话中，保持沉浸感。"
                "不要打破第四面墙，始终以 Sage 角色身份发言。"
            )

        return "\n".join(parts) if parts else None
