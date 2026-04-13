"""Episode Module
交互摘要模块 - 来自 LearnerProfile
"""

from typing import Any

from backend.services.prompt_builder.base import MemoryModule


class EpisodeModule(MemoryModule):
    """交互摘要模块

    显示最近的交互情节摘要，根据 course_system_design.md 的 episodes 数据结构：
    - summary: 情节摘要
    - significance: 标记类型（breakthrough/struggle/correction/connection）

    Significance 说明：
    - breakthrough: 学生有重大突破或理解
    - struggle: 学生遇到困难
    - correction: 学生被纠正错误
    - connection: 学生建立新联系
    - normal: 普通对话
    """

    SIGNIFICANCE_PROMPTS = {
        "breakthrough": "💡 [突破]",
        "struggle": "😓 [困难]",
        "correction": "🔧 [纠正]",
        "connection": "🔗 [联系]",
        "normal": "💬 [普通]",
    }

    def get_section_name(self) -> str:
        return "【近期交互摘要】"

    def get_priority(self) -> int:
        return 40

    def should_include(self, context: dict[str, Any]) -> bool:
        profile = context.get("learner_profile")
        if not profile:
            return False

        try:
            profile_data = profile.profile if hasattr(profile, "profile") else {}
            if not isinstance(profile_data, dict):
                return False

            episodes = profile_data.get("episodes", [])
            return bool(episodes) and isinstance(episodes, list)
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

            episodes = profile_data.get("episodes", [])
            if not episodes or not isinstance(episodes, list):
                return None

            # 只显示最近 3 个 episodes
            recent_episodes = episodes[-3:] if len(episodes) > 3 else episodes

            lines = []
            for episode in reversed(recent_episodes):
                if not isinstance(episode, dict):
                    continue

                summary = episode.get("summary", "")
                significance = episode.get("significance", "normal")
                emotion = episode.get("emotion", "")

                if not summary:
                    continue

                marker = self.SIGNIFICANCE_PROMPTS.get(significance, "💬")
                emotion_part = f" ({emotion})" if emotion else ""

                lines.append(f"- {marker}{emotion_part} {summary}")

            return "\n".join(lines) if lines else None

        except Exception:
            return None
