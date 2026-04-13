"""Scaffold Context
脚手架上下文提供者 - 基于 ZPD 的自适应支持
"""

from typing import Any

from backend.services.prompt_builder.base import ContextProvider


class ScaffoldContext(ContextProvider):
    """脚手架上下文提供者

    基于 Vygotsky 的最近发展区（ZPD）理论：
    - 高支持：当学习者处于挣扎区时
    - 低支持：当学习者处于舒适区/掌握区时

    脚手架等级 1-5：
    - 5: 最高支持 - 逐步引导
    - 4: 高支持 - 提供线索
    - 3: 适度支持 - 引导性问题
    - 2: 低支持 - 方向性暗示
    - 1: 最低支持 - 完全自主推理
    """

    SCAFFOLD_INSTRUCTIONS = {
        5: "【脚手架等级 5/5 — 最高支持】\n用最简单的类比一步步解释，直接给出具体示例带着学习者走。将问题拆解为最小步骤，每步都确认理解后再进入下一步。",
        4: "【脚手架等级 4/5 — 高支持】\n提供关键线索和提示，缩小思考范围。给出相关概念的对比，引导学习者在有限选项中推理。",
        3: "【脚手架等级 3/5 — 适度支持】\n提出引导性问题，给适度提示。让学习者尝试自己组织答案，在关键卡点时给予方向性帮助。",
        2: "【脚手架等级 2/5 — 低支持】\n仅给方向性暗示，鼓励自主探索。可以反问学习者的推理过程，但不直接揭示答案的方向。",
        1: "【脚手架等级 1/5 — 最低支持】\n只确认方向正确与否，让学生完全自主推理。提出更深层的延伸问题，推动学习者突破舒适区。",
    }

    def get_priority(self) -> int:
        return 2

    def should_include(self, context: dict[str, Any]) -> bool:
        return True

    def assemble(self, context: dict[str, Any]) -> str | None:
        try:
            prev_emotion = context.get("prev_emotion", {})
            mastery_level = context.get("mastery_level", 50)

            emotion_type = prev_emotion.get("emotion_type", "neutral")
            scaffold_level = self.compute_scaffold_level(emotion_type, mastery_level)
            scaffold_text = self.SCAFFOLD_INSTRUCTIONS.get(scaffold_level, self.SCAFFOLD_INSTRUCTIONS[3])

            # 添加学习者状态摘要
            status = f"【学习者状态】情感: {emotion_type} | 知识掌握度: {mastery_level}/100\n{scaffold_text}"

            return status

        except Exception:
            return None

    @staticmethod
    def compute_scaffold_level(emotion_type: str, mastery_level: int) -> int:
        """计算脚手架等级（1-5）

        基于模糊逻辑，根据情感类型和掌握度计算。
        """
        if emotion_type == "frustration" and mastery_level < 30:
            return 5
        if emotion_type == "frustration":
            return 4
        if emotion_type == "confusion" and mastery_level < 50:
            return 4
        if emotion_type == "confusion":
            return 3
        if emotion_type == "anxiety" and mastery_level > 60:
            return 3
        if emotion_type == "anxiety":
            return 4
        if emotion_type == "boredom" and mastery_level > 60:
            return 2
        if emotion_type == "boredom":
            return 3
        if emotion_type == "curiosity" and mastery_level > 60:
            return 2
        if emotion_type == "curiosity":
            return 3
        if emotion_type == "excitement" and mastery_level > 70:
            return 1
        if emotion_type == "excitement":
            return 2
        if emotion_type == "satisfaction" and mastery_level > 70:
            return 1
        if emotion_type == "satisfaction":
            return 2
        # neutral or unknown
        if mastery_level > 70:
            return 2
        if mastery_level < 30:
            return 4
        return 3
