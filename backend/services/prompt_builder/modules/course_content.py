"""Course Content Module

将 Course.meta 中由 AI 生成的课程结构（概览、章节、概念图）注入提示词，
让教学引擎基于教材内容进行授课，而非泛泛而谈。

Phase 3 Step 3: 课程感知教学集成
"""

from backend.services.prompt_builder.base import MemoryModule


class CourseContentModule(MemoryModule):
    """课程内容模块

    从 Course.meta 读取 AI 生成的课程结构：
    - generated_overview: 课程概览
    - generated_lessons: 章节列表（title, description, order, concepts, prerequisites）
    - concept_map: 概念关系图
    - current_lesson_index: 当前教学进度（第几课）

    这是会话级静态层，教学过程中提供知识框架。
    """

    def get_section_name(self) -> str:
        return "【课程内容与教学计划】"

    def get_priority(self) -> int:
        return 12  # 在 Narrative(10) 之后，Misconception(30) 之前

    def is_applicable(self, context: dict) -> bool:
        """需要有 course_id 且课程有生成内容"""
        return context.get("course_id") is not None

    def should_include(self, context: dict) -> bool:
        """课程有生成内容时始终注入"""
        return True

    def assemble(self, context: dict) -> str:
        """从 Course.meta 读取生成内容并渲染教学提示"""
        db = context.get("db")
        course_id = context.get("course_id")

        if not db or not course_id:
            return ""

        from backend.models.models import Course

        course = db.query(Course).filter(Course.id == course_id).first()
        if not course or not course.meta:
            return ""

        meta = course.meta
        parts = []

        # 1. 课程概览
        overview = meta.get("generated_overview")
        if overview:
            parts.append(f"## 课程概览\n{overview}")

        # 2. 章节列表 + 当前进度
        lessons = meta.get("generated_lessons", [])
        if lessons:
            current_idx = meta.get("current_lesson_index", 0)
            parts.append(self._render_lessons(lessons, current_idx))

        # 3. 概念图
        concept_map = meta.get("concept_map")
        if concept_map:
            parts.append(self._render_concept_map(concept_map))

        # 4. 教学指引
        if overview or lessons:
            parts.append(self._render_teaching_guidance(lessons, meta))

        return "\n\n".join(parts)

    def _render_lessons(self, lessons: list, current_idx: int) -> str:
        """渲染章节列表，标注当前进度"""
        lines = ["## 教学章节"]

        for i, lesson in enumerate(lessons):
            title = lesson.get("title", f"第{i+1}课")
            desc = lesson.get("description", "")
            concepts = lesson.get("concepts", [])
            prerequisites = lesson.get("prerequisites", [])

            if i == current_idx:
                marker = "> **[当前章节]**"
            elif i < current_idx:
                marker = "[v] [已完成]"
            else:
                marker = "[ ] [待学习]"

            line = f"{marker} **第{i+1}课: {title}**"
            if desc:
                line += f"\n   {desc}"
            if concepts:
                line += f"\n   核心概念: {', '.join(concepts[:5])}"
            if prerequisites:
                line += f"\n   前置要求: {', '.join(prerequisites[:3])}"

            lines.append(line)

        return "\n".join(lines)

    def _render_concept_map(self, concept_map: dict) -> str:
        """渲染概念图"""
        if not concept_map:
            return ""

        lines = ["## 核心概念关系"]

        nodes = concept_map.get("nodes", [])
        edges = concept_map.get("edges", [])

        if nodes:
            concept_names = [n.get("name", n.get("label", str(n))) for n in nodes[:10]]
            lines.append(f"关键概念: {', '.join(concept_names)}")

        if edges:
            relations = []
            for edge in edges[:8]:
                source = edge.get("source", edge.get("from", ""))
                target = edge.get("target", edge.get("to", ""))
                relation = edge.get("relation", edge.get("label", "→"))
                if source and target:
                    relations.append(f"{source} —[{relation}]→ {target}")
            if relations:
                lines.append("概念关系:\n" + "\n".join(f"  - {r}" for r in relations))

        return "\n".join(lines)

    def _render_teaching_guidance(self, lessons: list, meta: dict) -> str:
        """渲染教学指引"""
        lines = [
            "## 教学指引",
            "请基于上述课程内容进行教学：",
            "1. 围绕当前章节的核心概念展开提问和讨论",
            "2. 确认学生理解了前置概念后再推进新内容",
            "3. 当学生掌握了当前章节的核心概念后，可以自然过渡到下一章节",
            "4. 引用课程概览中的知识框架帮助建立体系化认知",
        ]

        current_idx = meta.get("current_lesson_index", 0)
        if lessons and 0 <= current_idx < len(lessons):
            current = lessons[current_idx]
            title = current.get("title", "")
            concepts = current.get("concepts", [])
            if title:
                lines.append(f"当前教学重点: **{title}**")
            if concepts:
                lines.append(f"请围绕以下概念引导学生: {', '.join(concepts[:5])}")

        return "\n".join(lines)