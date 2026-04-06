"""Relationship Context
关系阶段上下文提供者
"""

from typing import Any

from backend.services.prompt_builder.base import ContextProvider


class RelationshipContext(ContextProvider):
    """关系阶段上下文提供者
    
    根据 relationship_theory.md 的四维关系模型：
    - Trust（信任）
    - Familiarity（默契）
    - Respect（敬意）
    - Comfort（舒适）
    
    派生五个阶段：
    - stranger / acquaintance / friend / mentor / partner
    """
    
    STAGE_PROMPTS = {
        "stranger": "以温和、耐心的方式自我介绍，建立信任。使用简单易懂的语言，避免过于专业术语。",
        "acquaintance": "开始更多互动，逐步了解学习者的背景和需求。保持友好但适当的距离。",
        "friend": "以朋友的方式交流，可以更加轻松随意。分享学习方法，适度关心学习者的状态。",
        "mentor": "提供专业、深入的指导。鼓励学习者挑战更高难度，分享专业知识见解。",
        "partner": "深入讨论知识话题，共同探索。认可学习者的成长，可以进行更深层次的学术交流。",
    }
    
    def get_priority(self) -> int:
        return 1
    
    def should_include(self, context: dict[str, Any]) -> bool:
        return True
    
    def assemble(self, context: dict[str, Any]) -> str | None:
        try:
            relationship = context.get("relationship", {})
            stage = relationship.get("stage", "stranger")
            
            parts = []
            parts.append(f"【当前关系阶段：{stage}】")
            
            stage_prompt = self.STAGE_PROMPTS.get(stage, self.STAGE_PROMPTS["stranger"])
            parts.append(stage_prompt)
            
            # 添加关系维度信息（可选）
            dimensions = relationship.get("dimensions", {})
            if dimensions:
                dim_lines = []
                for dim, value in dimensions.items():
                    if isinstance(value, (int, float)):
                        dim_lines.append(f"{dim}: {value:.2f}")
                if dim_lines:
                    parts.append(f"关系维度: {', '.join(dim_lines)}")
            
            return "\n".join(parts)
            
        except Exception:
            return None
