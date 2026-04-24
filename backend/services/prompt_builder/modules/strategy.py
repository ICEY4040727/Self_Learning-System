"""Strategy Module
教学策略模块 - 根据画像维度值匹配策略规则，注入"怎么教"的指令。

理论：Vygotsky ZPD — 低维度多引导，高维度少引导。
"""

import logging
from typing import Any

from backend.services.prompt_builder.base import MemoryModule

logger = logging.getLogger(__name__)


class StrategyModule(MemoryModule):
    """根据画像维度值匹配策略规则，注入教学调整指令。"""

    def get_section_name(self) -> str:
        return "【教学策略】"

    def get_priority(self) -> int:
        return 25  # 在 Misconception(30) 之前

    def should_include(self, context: dict[str, Any]) -> bool:
        db = context.get("db")
        learner_profile = context.get("learner_profile")
        return db is not None and learner_profile is not None

    def assemble(self, context: dict[str, Any]) -> str | None:
        db = context.get("db")
        learner_profile = context.get("learner_profile")
        scene = context.get("scene", "learning")

        if not db or not learner_profile:
            return None

        try:
            from backend.models.models import StrategyRule

            # Get dimension_scores from profile
            profile = learner_profile.profile if isinstance(learner_profile.profile, dict) else {}
            dimension_scores = profile.get("dimension_scores") or {}

            if not dimension_scores:
                return None

            # Load matching rules
            rules = db.query(StrategyRule).filter(
                StrategyRule.enabled == True,
                StrategyRule.dimension_key.in_(dimension_scores.keys()),
            ).order_by(StrategyRule.priority).all()

            if not rules:
                return None

            instructions = []
            for rule in rules:
                score = dimension_scores.get(rule.dimension_key)
                if score is None:
                    continue

                # Check scene match
                if rule.scene != "all" and rule.scene != scene:
                    continue

                # Match instruction by score range
                instruction = None
                if score < 0.4:
                    instruction = rule.low_instruction
                elif score <= 0.7:
                    instruction = rule.mid_instruction  # may be None = 不干预
                else:
                    instruction = rule.high_instruction

                if instruction:
                    instructions.append(f"- {instruction}")

            if not instructions:
                return None

            return "\n".join(instructions)

        except Exception as e:
            logger.warning(f"StrategyModule failed: {e}")
            return None