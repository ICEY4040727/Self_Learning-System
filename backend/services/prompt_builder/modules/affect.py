"""Affect Module
情感模式模块 - 来自 LearnerProfile
"""

from typing import Any

from backend.services.prompt_builder.base import MemoryModule


class AffectModule(MemoryModule):
    """情感模式模块
    
    从 LearnerProfile 中提取情感模式信息。
    """
    
    def get_section_name(self) -> str:
        return "【情感模式】"
    
    def get_priority(self) -> int:
        return 60
    
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
            
            affect = profile_data.get("affect", {})
            if not affect or not isinstance(affect, dict):
                return None
            
            lines = []
            for key, value in affect.items():
                if isinstance(value, dict):
                    val = value.get("value")
                    if val is not None:
                        lines.append(f"{key}: {val}")
                elif value:
                    lines.append(f"{key}: {value}")
            
            return ", ".join(lines) if lines else None
            
        except Exception:
            return None
