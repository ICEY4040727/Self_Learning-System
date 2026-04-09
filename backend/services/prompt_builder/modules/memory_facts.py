"""Memory Facts Module
记忆事实模块 - 从 memory_facts 表检索记忆注入提示词

替代原 knowledge.py 的记忆检索功能。
"""

import logging
from typing import Any

from backend.services.memory_facts import memory_facts_service
from backend.services.prompt_builder.base import MemoryModule

logger = logging.getLogger(__name__)


class MemoryFactsModule(MemoryModule):
    """
    记忆事实模块
    
    从 memory_facts 表检索相关记忆，按 salience 降序排列。
    用于为 AI 提供关于学生的认知上下文。
    """
    
    def get_section_name(self) -> str:
        return "【学生认知记忆】"
    
    def get_priority(self) -> int:
        return 70  # 较高优先级
    
    def should_include(self, context: dict[str, Any]) -> bool:
        db = context.get("db")
        character_id = context.get("character_id")  # sage character id
        
        # 需要数据库会话和角色 ID
        return db is not None and character_id is not None
    
    def assemble(self, context: dict[str, Any]) -> str | None:
        db = context.get("db")
        character_id = context.get("character_id")
        world_id = context.get("world_id")
        current_topic = context.get("user_message", "")
        
        if not db or not character_id:
            return None
        
        try:
            # 检索记忆
            memories = memory_facts_service.retrieve_memories(
                db=db,
                character_id=character_id,
                world_id=world_id,
                query=current_topic if len(current_topic) > 5 else None,
                limit=8,
                min_salience=0.4,
            )
            
            if not memories:
                return None
            
            lines = []
            for mem in memories:
                # 格式化记忆内容
                fact_type_label = {
                    "student_state": "状态",
                    "concept_struggle": "困难",
                    "concept_mastered": "掌握",
                    "preference": "偏好",
                    "event": "事件",
                    "commitment": "约定",
                }.get(mem.fact_type, mem.fact_type)
                
                # 根据 salience 添加标记
                salience_marker = ""
                if mem.salience >= 0.8:
                    salience_marker = "⭐"
                elif mem.salience >= 0.6:
                    salience_marker = "📌"
                
                content = mem.content[:100] + "..." if len(mem.content) > 100 else mem.content
                lines.append(f"- [{fact_type_label}]{salience_marker} {content}")
            
            return "\n".join(lines)
            
        except Exception as e:
            logger.warning(f"MemoryFactsModule failed: {e}")
            return None
