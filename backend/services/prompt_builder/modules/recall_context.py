"""Recall Context Module
上下文化记忆召回模块 - 从 RecallService 获取前置概念关联提示。

与 MemoryFactsModule 互补：
- MemoryFactsModule 注入原始事实列表
- RecallContextModule 注入上下文化的教学提示
"""

import logging
from typing import Any

from backend.services.prompt_builder.base import MemoryModule
from backend.services.recall_service import recall_service

logger = logging.getLogger(__name__)


class RecallContextModule(MemoryModule):
    """上下文化记忆召回 - 前置概念关联提示。"""

    def get_section_name(self) -> str:
        return "【记忆召回上下文】"

    def get_priority(self) -> int:
        return 75  # 在 MemoryFacts(70) 之后

    def should_include(self, context: dict[str, Any]) -> bool:
        db = context.get("db")
        character_id = context.get("character_id")
        course_id = context.get("course_id")
        return db is not None and character_id is not None and course_id is not None

    def assemble(self, context: dict[str, Any]) -> str | None:
        db = context.get("db")
        character_id = context.get("character_id")
        world_id = context.get("world_id")
        course_id = context.get("course_id")

        if not all([db, character_id, course_id]):
            return None

        try:
            hints = recall_service.get_recall_hints(
                db,
                character_id=character_id,
                world_id=world_id,
                current_topic=context.get("current_topic"),
                course_id=course_id,
            )

            if not hints:
                return None

            return "\n".join(f"- {h}" for h in hints)

        except Exception as e:
            logger.warning(f"RecallContextModule failed: {e}")
            return None