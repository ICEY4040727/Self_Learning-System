"""Knowledge Module
知识状态模块 - 按 Bloom 认知层级分组
"""

from typing import Any

from backend.services.knowledge import knowledge_service
from backend.services.prompt_builder.base import MemoryModule


class KnowledgeModule(MemoryModule):
    """知识状态模块 - 按 Bloom 认知层级分组
    
    将概念按掌握度分组：
    - 已掌握(apply+): mastery >= 0.8
    - 学习中(understand): 0.4 <= mastery < 0.8
    - 初识(remember): mastery < 0.4
    """
    
    def get_section_name(self) -> str:
        return "【当前知识状态】"
    
    def get_priority(self) -> int:
        return 10
    
    def should_include(self, context: dict[str, Any]) -> bool:
        return True  # 始终包含
    
    def assemble(self, context: dict[str, Any]) -> str | None:
        db = context.get("db")
        world_id = context.get("world_id")
        
        if not db or not world_id:
            return None
        
        try:
            graph = knowledge_service.get_knowledge(db, world_id)
            concepts = graph.get("concepts", {})
            
            if not concepts:
                return None
            
            # 按掌握度分组（Bloom 认知层级）
            mastered = []      # mastery >= 0.8 (apply+)
            learning = []     # 0.4 <= mastery < 0.8 (understand)
            new = []          # mastery < 0.4 (remember)
            
            for concept_id, concept in concepts.items():
                if not isinstance(concept, dict):
                    continue
                mastery = float(concept.get("mastery", 0.0))
                name = concept.get("name", concept_id)
                
                if mastery >= 0.8:
                    mastered.append((name, mastery))
                elif mastery >= 0.4:
                    learning.append((name, mastery))
                else:
                    new.append((name, mastery))
            
            lines = []
            
            # 按掌握度降序排序
            mastered.sort(key=lambda x: x[1], reverse=True)
            learning.sort(key=lambda x: x[1], reverse=True)
            new.sort(key=lambda x: x[1], reverse=True)
            
            if mastered:
                names = ", ".join(f"{name}({m:.1f})" for name, m in mastered[:5])
                lines.append(f"已掌握(apply+): {names}")
            if learning:
                names = ", ".join(f"{name}({m:.1f})" for name, m in learning[:5])
                lines.append(f"学习中(understand): {names}")
            if new:
                names = ", ".join(f"{name}({m:.1f})" for name, m in new[:5])
                lines.append(f"初识(remember): {names}")
            
            return "\n".join(lines) if lines else None
            
        except Exception:
            return None
