"""Dynamic analysis module for emotion detection and relationship stage tracking.

Supports 8 education-specific emotion categories with two analysis modes:
- LLM-based structured classification (primary, when API key available)
- Enhanced weighted keyword matching (fallback)
"""

import json
import logging
import re

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Emotion taxonomy – 8 categories designed for educational dialogue
# ---------------------------------------------------------------------------
EDUCATION_EMOTIONS = {
    "curiosity":    {"valence": 0.70, "arousal": 0.70, "zh": "好奇"},
    "confusion":    {"valence": 0.30, "arousal": 0.60, "zh": "困惑"},
    "frustration":  {"valence": 0.20, "arousal": 0.75, "zh": "沮丧"},
    "excitement":   {"valence": 0.85, "arousal": 0.80, "zh": "兴奋"},
    "satisfaction":  {"valence": 0.80, "arousal": 0.40, "zh": "满足"},
    "boredom":      {"valence": 0.30, "arousal": 0.20, "zh": "无聊"},
    "anxiety":      {"valence": 0.25, "arousal": 0.80, "zh": "焦虑"},
    "neutral":      {"valence": 0.50, "arousal": 0.50, "zh": "平静"},
}

# ---------------------------------------------------------------------------
# LLM prompt for structured emotion classification
# ---------------------------------------------------------------------------
EMOTION_ANALYSIS_PROMPT = """\
你是一个学生情感分析器。根据学生在学习对话中发送的消息，判断其当前情感状态。

仅从以下类别中选择一个：
- curiosity: 好奇，想探索，主动提问
- confusion: 困惑，不理解，需要澄清
- frustration: 沮丧，受挫，感觉卡住
- excitement: 兴奋，恍然大悟，有突破
- satisfaction: 满意，理解了，感谢
- boredom: 无聊，不感兴趣，敷衍
- anxiety: 焦虑，紧张，有压力
- neutral: 平静，陈述事实，无明显情感

仅返回 JSON，不要有其他内容：
{"emotion_type": "<类别>", "confidence": <0.0-1.0>}

学生消息："""


class DynamicAnalyzer:
    """Dynamic analyzer for emotion detection and relationship tracking"""

    def __init__(self):
        self._keyword_patterns = self._build_keyword_patterns()

    # ------------------------------------------------------------------
    # Keyword pattern table
    # ------------------------------------------------------------------
    @staticmethod
    def _build_keyword_patterns() -> dict:
        return {
            "curiosity": {
                "keywords": [
                    # Chinese
                    "为什么", "怎么", "如何", "什么是", "能不能解释", "想知道", "想了解",
                    "好奇", "请问", "是否可以", "有没有", "告诉我", "能否", "可不可以",
                    "想请教", "请教", "有什么", "怎样", "是什么",
                    # English
                    "why", "how", "what is", "can you explain", "tell me about",
                    "curious", "wonder", "interested in", "what if", "i want to know",
                ],
                "weight": 1.0,
            },
            "confusion": {
                "keywords": [
                    "不懂", "不理解", "不明白", "困惑", "搞不清", "看不懂", "什么意思",
                    "没听懂", "迷糊", "晕了", "搞混了", "分不清", "没搞明白", "不太懂",
                    "还是不太", "没有理解", "有点乱",
                    "confused", "don't understand", "don't get it", "unclear", "lost",
                    "what do you mean", "makes no sense", "not sure i follow",
                ],
                "weight": 1.2,
            },
            "frustration": {
                "keywords": [
                    "太难了", "做不到", "放弃", "不想学了", "受不了", "烦死了",
                    "崩溃", "算了", "没用", "不行", "学不会", "越学越糊涂", "真的不会",
                    "frustrated", "too hard", "give up", "impossible", "can't do this",
                    "hate this", "annoying", "stuck", "useless",
                ],
                "weight": 1.3,
            },
            "excitement": {
                "keywords": [
                    "太好了", "原来如此", "明白了", "懂了", "厉害", "哇", "酷",
                    "有意思", "好棒", "终于", "恍然大悟", "茅塞顿开", "原来是这样",
                    "突然明白", "太有趣了", "学到了",
                    "aha", "oh i see", "got it", "awesome", "amazing", "wow",
                    "finally", "eureka", "that's it", "brilliant", "so that's why",
                ],
                "weight": 1.1,
            },
            "satisfaction": {
                "keywords": [
                    "谢谢", "感谢", "理解了", "清楚了", "好的", "明白",
                    "收获很大", "不错", "挺好", "学到很多", "谢谢老师", "辛苦了",
                    "thank", "understood", "clear now", "helpful", "great explanation",
                    "learned a lot", "appreciate",
                ],
                "weight": 0.9,
            },
            "boredom": {
                "keywords": [
                    "无聊", "没意思", "知道了", "随便", "都行", "嗯嗯",
                    "好吧", "行吧",
                    "boring", "bored", "whatever", "already know",
                    "move on", "skip", "next topic",
                ],
                "weight": 0.8,
            },
            "anxiety": {
                "keywords": [
                    "担心", "害怕", "紧张", "压力大", "焦虑", "来不及", "怎么办",
                    "完了", "糟糕", "急死了", "考试", "赶不上",
                    "worried", "nervous", "anxious", "stressed", "pressure",
                    "scared", "afraid", "panic", "overwhelmed",
                ],
                "weight": 1.2,
            },
        }

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    async def analyze_emotion(
        self,
        text: str,
        user_api_key: str = None,
        provider: str = None,
    ) -> dict:
        """
        Analyze emotion from text.

        Uses LLM-based analysis when API key is available, falls back to
        enhanced local keyword matching otherwise.

        Returns dict with: valence, arousal, emotion_type, confidence
        """
        if user_api_key and provider:
            try:
                result = await self._llm_analyze(text, user_api_key, provider)
                if result:
                    return result
            except Exception as e:
                logger.warning("LLM emotion analysis failed, using local fallback: %s", e)

        return self._local_analyze(text)

    # ------------------------------------------------------------------
    # LLM-based analysis
    # ------------------------------------------------------------------
    async def _llm_analyze(
        self, text: str, user_api_key: str, provider: str
    ) -> dict | None:
        """Call LLM for structured emotion classification."""
        from backend.services.llm.adapter import get_llm_adapter

        adapter = get_llm_adapter(provider)
        prompt = EMOTION_ANALYSIS_PROMPT + text[:500]

        response = await adapter.chat(
            messages=[{"role": "user", "content": prompt}],
            system_prompt="你是情感分类器，仅输出JSON。",
            user_api_key=user_api_key,
        )

        try:
            json_match = re.search(r"\{[^}]+\}", response)
            if not json_match:
                return None

            data = json.loads(json_match.group())
            emotion_type = data.get("emotion_type", "neutral")
            confidence = float(data.get("confidence", 0.7))

            if emotion_type not in EDUCATION_EMOTIONS:
                return None

            meta = EDUCATION_EMOTIONS[emotion_type]
            return {
                "valence": meta["valence"],
                "arousal": meta["arousal"],
                "emotion_type": emotion_type,
                "confidence": round(min(confidence, 1.0), 2),
            }
        except (json.JSONDecodeError, ValueError, TypeError):
            return None

    # ------------------------------------------------------------------
    # Local keyword-based analysis (fallback)
    # ------------------------------------------------------------------
    def _local_analyze(self, text: str) -> dict:
        """Enhanced keyword matching with weighted scoring across 8 emotions."""
        text_lower = text.lower()
        scores: dict[str, float] = {}

        for emotion, config in self._keyword_patterns.items():
            score = 0.0
            for keyword in config["keywords"]:
                if keyword in text_lower:
                    score += config["weight"]
            scores[emotion] = score

        best_emotion = max(scores, key=scores.get) if scores else "neutral"
        best_score = scores.get(best_emotion, 0.0)

        if best_score > 0:
            meta = EDUCATION_EMOTIONS[best_emotion]
            confidence = round(min(0.85, 0.45 + best_score * 0.1), 2)
            return {
                "valence": meta["valence"],
                "arousal": meta["arousal"],
                "emotion_type": best_emotion,
                "confidence": confidence,
            }

        # No keyword match → neutral
        return {
            "valence": 0.50,
            "arousal": 0.50,
            "emotion_type": "neutral",
            "confidence": 0.4,
        }

    # ------------------------------------------------------------------
    # Relationship stage tracking
    # ------------------------------------------------------------------
    async def update_relationship_stage(self, session_id: int, emotion: dict, db=None) -> str:
        """
        Update relationship stage based on emotion and interaction count.
        Stages: stranger -> acquaintance -> friend -> mentor -> partner
        """
        from backend.db.database import SessionLocal
        from backend.models.models import ChatMessage

        own_db = False
        if not db:
            db = SessionLocal()
            own_db = True

        try:
            message_count = db.query(ChatMessage).filter(
                ChatMessage.session_id == session_id
            ).count()

            # Use average valence of recent messages instead of single message
            recent_msgs = (
                db.query(ChatMessage)
                .filter(
                    ChatMessage.session_id == session_id,
                    ChatMessage.sender_type == "user",
                    ChatMessage.emotion_analysis != None,
                )
                .order_by(ChatMessage.timestamp.desc())
                .limit(10)
                .all()
            )
            if recent_msgs:
                valence = sum(
                    m.emotion_analysis.get("valence", 0.5) for m in recent_msgs
                ) / len(recent_msgs)
            else:
                valence = emotion.get("valence", 0.5)

            if message_count >= 30 and valence > 0.7:
                return "partner"
            elif message_count >= 20 and valence > 0.6:
                return "mentor"
            elif message_count >= 10 and valence > 0.5:
                return "friend"
            elif message_count >= 3:
                return "acquaintance"
            else:
                return "stranger"
        finally:
            if own_db:
                db.close()

    async def update_learner_profile(self, user_id: int, world_id: int, interaction: dict, db=None):
        """Update learner profile based on interaction data."""
        from backend.db.database import SessionLocal
        from backend.models.models import LearnerProfile

        own_db = False
        if not db:
            db = SessionLocal()
            own_db = True

        try:
            profile_row = db.query(LearnerProfile).filter(
                LearnerProfile.user_id == user_id,
                LearnerProfile.world_id == world_id,
            ).first()
            if not profile_row:
                profile_row = LearnerProfile(
                    user_id=user_id,
                    world_id=world_id,
                    profile={"preferences": {}, "affect": {}, "metacognition": {}},
                )
                db.add(profile_row)
                db.flush()

            profile = profile_row.profile if isinstance(profile_row.profile, dict) else {}
            preferences = dict(profile.get("preferences") or {})
            affect = dict(profile.get("affect") or {})
            metacognition = dict(profile.get("metacognition") or {})

            emotion_type = (interaction or {}).get("emotion_type")
            if emotion_type:
                affect["last_emotion"] = emotion_type
                affect[f"count_{emotion_type}"] = int(affect.get(f"count_{emotion_type}", 0)) + 1

            user_message = str((interaction or {}).get("message", "")).strip()
            if "例子" in user_message or "example" in user_message.lower():
                preferences["example_first"] = True
            if "步骤" in user_message or "step" in user_message.lower():
                preferences["step_by_step"] = True

            confidence = (interaction or {}).get("confidence")
            if isinstance(confidence, (int, float)):
                metacognition["self_confidence"] = round(float(confidence), 3)

            profile_row.profile = {
                "preferences": preferences,
                "affect": affect,
                "metacognition": metacognition,
            }
            db.flush()
            return profile_row.profile
        finally:
            if own_db:
                db.commit()
                db.close()
