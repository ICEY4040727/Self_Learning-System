"""Memory Retrieval Module
记忆检索模块 - 从知识图谱中检索相关记忆
"""

import logging
from typing import Any

from backend.services.prompt_builder.base import MemoryModule

logger = logging.getLogger(__name__)


class MemoryRetrievalModule(MemoryModule):
    """记忆检索模块
    
    从知识图谱的 episodes 中检索相关记忆。
    """
    
    def get_section_name(self) -> str:
        return "【相关学习记忆】"
    
    def get_priority(self) -> int:
        return 80
    
    def should_include(self, context: dict[str, Any]) -> bool:
        db = context.get("db")
        world_id = context.get("world_id")
        return db is not None and world_id is not None
    
    def assemble(self, context: dict[str, Any]) -> str | None:
        db = context.get("db")
        world_id = context.get("world_id")
        current_topic = context.get("user_message", "")
        checkpoint_time = context.get("checkpoint_time")
        
        if not db or not world_id:
            return None
        
        try:
            # 使用 knowledge_service 检索记忆
            from backend.services.knowledge import knowledge_service
            
            memories = knowledge_service.retrieve_memories(
                db=db,
                world_id=world_id,
                current_topic=current_topic,
                checkpoint_time=checkpoint_time,
                limit=5
            )
            
            if not memories:
                return None
            
            lines = []
            for memory in memories:
                content = memory.get("content", "")
                significance = memory.get("significance", "normal")
                
                # 添加标记
                marker = ""
                if significance == "breakthrough":
                    marker = "💡 "
                elif significance == "struggle":
                    marker = "😓 "
                
                lines.append(f"- {marker}{content}")
            
            return "\n".join(lines)
            
        except Exception as e:
            logger.warning(f"MemoryRetrievalModule failed: {e}")
            return None
