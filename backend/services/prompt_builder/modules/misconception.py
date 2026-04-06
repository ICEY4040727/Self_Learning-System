"""Misconception Module
误解追踪模块 - 来自 LearnerProfile
"""

from typing import Any

from backend.services.prompt_builder.base import MemoryModule


class MisconceptionModule(MemoryModule):
    """误解追踪模块
    
    追踪学生错误认知，根据 learning_memory_theory.md 的 ITS Perturbation Model：
    - "不知道" → 教
    - "错误地知道" → 先破再立
    
    严重程度：
    - critical: 严重误解，需要立即纠正
    - moderate: 中度误解
    - minor: 轻微误解
    """
    
    SEVERITY_PROMPTS = {
        "critical": "⚠️ [严重误解]",
        "moderate": "⚠️ [中度误解]",
        "minor": "⚠️ [轻微误解]",
    }
    
    def get_section_name(self) -> str:
        return "【误解追踪】"
    
    def get_priority(self) -> int:
        return 30
    
    def should_include(self, context: dict[str, Any]) -> bool:
        profile = context.get("learner_profile")
        if not profile:
            return False
        
        try:
            profile_data = profile.profile if hasattr(profile, "profile") else {}
            if not isinstance(profile_data, dict):
                return False
            
            misconceptions = profile_data.get("misconceptions", {})
            return bool(misconceptions) and isinstance(misconceptions, dict)
        except Exception:
            return False
    
    def assemble(self, context: dict[str, Any]) -> str | None:
        profile = context.get("learner_profile")
        if not profile:
            return None
        
        try:
            profile_data = profile.profile if hasattr(profile, "profile") else {}
            if not isinstance(profile_data, dict):
                return None
            
            misconceptions = profile_data.get("misconceptions", {})
            if not misconceptions or not isinstance(misconceptions, dict):
                return None
            
            # 只显示未纠正的误解（t_invalid 为空）
            active_misconceptions = []
            for mis_id, mis_data in misconceptions.items():
                if isinstance(mis_data, dict):
                    # 跳过已纠正的误解
                    if mis_data.get("t_invalid") is not None:
                        continue
                    
                    name = mis_data.get("name", mis_id)
                    severity = mis_data.get("severity", "moderate")
                    content = mis_data.get("content", "")
                    related_concept = mis_data.get("related_concept", "")
                    
                    severity_marker = self.SEVERITY_PROMPTS.get(severity, "⚠️")
                    related = f" → 正确认知: {related_concept}" if related_concept else ""
                    
                    active_misconceptions.append({
                        "severity": severity,
                        "text": f"{severity_marker} {name}: {content}{related}"
                    })
            
            if not active_misconceptions:
                return None
            
            # 按严重程度排序
            severity_order = {"critical": 0, "moderate": 1, "minor": 2}
            active_misconceptions.sort(key=lambda x: severity_order.get(x["severity"], 1))
            
            lines = [m["text"] for m in active_misconceptions]
            return "\n".join(lines)
            
        except Exception:
            return None
