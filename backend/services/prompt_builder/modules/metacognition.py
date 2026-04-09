"""Metacognition Module
元认知模块 - MSKT 四维度
"""

from typing import Any

from backend.services.prompt_builder.base import MemoryModule


class MetacognitionModule(MemoryModule):
    """元认知模块 - MSKT 四维度
    
    MSKT 四维度：
    - planning: 规划
    - monitoring: 监控
    - regulating: 调节
    - reflecting: 反思
    """
    
    MSKT_DIMENSIONS = ["planning", "monitoring", "regulating", "reflecting"]
    
    def get_section_name(self) -> str:
        return "【元认知】"
    
    def get_priority(self) -> int:
        return 70
    
    def should_include(self, context: dict[str, Any]) -> bool:
        return context.get("learner_profile") is not None
    
    def assemble(self, context: dict[str, Any]) -> str | None:
        profile = context.get("learner_profile")
        if not profile:
            return None
        
        try:
            profile_data = profile.profile if hasattr(profile, "profile") else {}
            if not isinstance(profile_data, dict):
                return None
            
            metacognition = profile_data.get("metacognition", {})
            if not metacognition or not isinstance(metacognition, dict):
                return None
            
            lines = []
            for dim in self.MSKT_DIMENSIONS:
                dim_data = metacognition.get(dim)
                if isinstance(dim_data, dict):
                    value = dim_data.get("value")
                    if value:
                        lines.append(f"{dim}: {value}")
            
            return ", ".join(lines) if lines else None
            
        except Exception:
            return None
