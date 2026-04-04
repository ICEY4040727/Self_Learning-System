from typing import Any

from backend.models.models import _default_relationship


def _clamp(value: float) -> float:
    return max(0.0, min(1.0, round(value, 3)))


class RelationshipService:
    def update_dimensions(
        self,
        session,
        user_msg: str,
        emotion: dict[str, Any] | None,
        episode_type: str = "dialogue",
    ) -> dict[str, Any]:
        relationship = dict(session.relationship or _default_relationship())
        dimensions = dict(relationship.get("dimensions") or _default_relationship()["dimensions"])

        emotion_type = (emotion or {}).get("emotion_type", "neutral")
        delta_map = {
            "curiosity": {"trust": 0.03, "familiarity": 0.04, "respect": 0.02, "comfort": 0.03},
            "excitement": {"trust": 0.04, "familiarity": 0.03, "respect": 0.03, "comfort": 0.04},
            "satisfaction": {"trust": 0.03, "familiarity": 0.02, "respect": 0.03, "comfort": 0.03},
            "neutral": {"trust": 0.01, "familiarity": 0.01, "respect": 0.01, "comfort": 0.01},
            "confusion": {"trust": 0.0, "familiarity": 0.01, "respect": -0.01, "comfort": -0.01},
            "frustration": {"trust": -0.02, "familiarity": 0.0, "respect": -0.01, "comfort": -0.03},
            "anxiety": {"trust": -0.01, "familiarity": 0.0, "respect": 0.0, "comfort": -0.02},
            "boredom": {"trust": -0.01, "familiarity": 0.0, "respect": -0.01, "comfort": -0.01},
        }
        deltas = delta_map.get(emotion_type, delta_map["neutral"])

        for key, delta in deltas.items():
            dimensions[key] = _clamp(float(dimensions.get(key, 0.0)) + delta)

        new_stage = self.derive_stage(dimensions)
        old_stage = relationship.get("stage", "stranger")
        history = list(relationship.get("history") or [])
        if new_stage != old_stage:
            history.append(
                {
                    "type": "stage_change",
                    "from": old_stage,
                    "to": new_stage,
                    "reason": emotion_type,
                    "episode_type": episode_type,
                    "message_preview": user_msg[:80],
                }
            )

        relationship["dimensions"] = dimensions
        relationship["stage"] = new_stage
        relationship["history"] = history[-50:]
        return relationship

    def derive_stage(self, dimensions: dict[str, Any]) -> str:
        avg = (
            float(dimensions.get("trust", 0.0))
            + float(dimensions.get("familiarity", 0.0))
            + float(dimensions.get("respect", 0.0))
            + float(dimensions.get("comfort", 0.0))
        ) / 4.0
        if avg >= 0.85:
            return "partner"
        if avg >= 0.65:
            return "mentor"
        if avg >= 0.45:
            return "friend"
        if avg >= 0.20:
            return "acquaintance"
        return "stranger"

    def check_events(
        self,
        old_relationship: dict[str, Any],
        new_relationship: dict[str, Any],
    ) -> list[dict[str, Any]]:
        events: list[dict[str, Any]] = []
        old_stage = old_relationship.get("stage", "stranger")
        new_stage = new_relationship.get("stage", "stranger")
        if new_stage != old_stage:
            events.append({"type": "stage_change", "from": old_stage, "to": new_stage})

        old_dims = old_relationship.get("dimensions", {})
        new_dims = new_relationship.get("dimensions", {})
        for key in ("trust", "familiarity", "respect", "comfort"):
            old_value = float(old_dims.get(key, 0.0))
            new_value = float(new_dims.get(key, 0.0))
            if old_value < 0.6 <= new_value:
                events.append({"type": "dimension_breakthrough", "dimension": key, "value": new_value})
        return events

    def get_instructions(self, dimensions: dict[str, Any]) -> str:
        trust = float(dimensions.get("trust", 0.0))
        comfort = float(dimensions.get("comfort", 0.0))
        if trust < 0.3:
            return "先建立安全感，多肯定学习者的表达，再逐步加深问题难度。"
        if comfort < 0.3:
            return "避免施压语气，保持温和提问，优先帮助学习者澄清思路。"
        if trust > 0.7 and comfort > 0.7:
            return "可使用更高阶的追问与挑战，引导学习者进行深层推理。"
        return "保持苏格拉底式引导，依据学习者反馈动态调整提问深度。"


relationship_service = RelationshipService()
