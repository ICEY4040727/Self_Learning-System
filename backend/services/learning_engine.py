"""Learning Engine - Core logic for Socratic learning system"""

# =============================================================================
# 命名规范说明:
#
# traveler vs learner 的区分:
#   - traveler: 游戏角色层 (Character.type="traveler", Session.traveler_character_id)
#              玩家在游戏世界中的化身，关联故事/叙事
#   - learner_profile: 学习追踪层 (LearnerProfile, Session.learner_profile_id)
#              记录用户的学习状态、偏好、元认知等信息
#
# 在会话(Session)中的关联:
#   - Session.traveler_character_id: 玩家扮演的旅人角色 (游戏角色)
#   - Session.learner_profile_id: 用户的学习档案 (学习追踪)
# =============================================================================

import json
import logging
import re
from types import SimpleNamespace

from sqlalchemy.orm import Session

from backend.db.database import SessionLocal
from backend.models.models import (
    Character,
    ChatMessage,
    Checkpoint,
    LearnerProfile,
    RelationshipStageRecord,
    TeacherPersona,
    _default_relationship,
)
from backend.models.models import (
    Session as SessionModel,
)
from backend.services.dynamic_analyzer import DynamicAnalyzer
from backend.services.knowledge import knowledge_service
from backend.services.llm.adapter import get_llm_adapter
from backend.services.relationship import relationship_service

logger = logging.getLogger(__name__)


class LearningEngine:
    """Learning engine for processing user messages and generating AI responses"""

    ROLE_MAP = {"user": "user", "teacher": "assistant"}

    def __init__(self):
        self.analyzer = DynamicAnalyzer()
        self.knowledge = knowledge_service
        self.relationship = relationship_service

    # ------------------------------------------------------------------
    # Relationship stage prompts
    # ------------------------------------------------------------------
    STAGE_PROMPTS = {
        "stranger": "以温和、耐心的方式自我介绍，建立信任。使用简单易懂的语言，避免过于专业术语。",
        "acquaintance": "开始更多互动，逐步了解学习者的背景和需求。保持友好但适当的距离。",
        "friend": "以朋友的方式交流，可以更加轻松随意。分享学习方法，适度关心学习者的状态。",
        "mentor": "提供专业、深入的指导。鼓励学习者挑战更高难度，分享专业知识见解。",
        "partner": "深入讨论知识话题，共同探索。认可学习者的成长，可以进行更深层次的学术交流。",
    }

    # Scaffold level instructions (ZPD-based)
    SCAFFOLD_INSTRUCTIONS = {
        5: "【脚手架等级 5/5 — 最高支持】\n用最简单的类比一步步解释，直接给出具体示例带着学习者走。将问题拆解为最小步骤，每步都确认理解后再进入下一步。",
        4: "【脚手架等级 4/5 — 高支持】\n提供关键线索和提示，缩小思考范围。给出相关概念的对比，引导学习者在有限选项中推理。",
        3: "【脚手架等级 3/5 — 适度支持】\n提出引导性问题，给适度提示。让学习者尝试自己组织答案，在关键卡点时给予方向性帮助。",
        2: "【脚手架等级 2/5 — 低支持】\n仅给方向性暗示，鼓励自主探索。可以反问学习者的推理过程，但不直接揭示答案的方向。",
        1: "【脚手架等级 1/5 — 最低支持】\n只确认方向正确与否，让学生完全自主推理。提出更深层的延伸问题，推动学习者突破舒适区。",
    }

    @staticmethod
    def compute_scaffold_level(emotion_type: str, mastery_level: int) -> int:
        """
        Compute scaffold level (1-5) using fuzzy logic on emotion + mastery.

        Based on Vygotsky's ZPD theory: high support when learner is in
        struggle zone, low support when in comfort/mastery zone.
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

    # ------------------------------------------------------------------
    # Dual-layer prompt builder
    # ------------------------------------------------------------------
    def build_system_prompt(
        self,
        teacher_persona: TeacherPersona,
        relationship_stage: str,
        relationship_instructions: str = "",
        learner_profile: LearnerProfile | None = None,
        retrieved_memories: list[dict] = None,
        prev_emotion: dict | None = None,
        mastery_level: int = 50,
        knowledge_context: str = "",
    ) -> str:
        """
        Build system prompt with dual-layer architecture:
          Static layer  — teacher identity + Socratic method principles
          Dynamic layer — relationship stage + scaffold + learner context + memories + knowledge graph
        """
        static = self._build_static_layer(teacher_persona)
        dynamic = self._build_dynamic_layer(
            relationship_instructions,
            relationship_stage, learner_profile, retrieved_memories,
            prev_emotion, mastery_level, knowledge_context,
        )
        return f"{static}\n\n---\n\n{dynamic}"

    def _build_static_layer(self, teacher_persona: TeacherPersona) -> str:
        """Stable across turns: persona identity + Socratic method rules."""
        persona = teacher_persona.system_prompt_template or ""
        if not persona:
            persona = (
                f"你是 {teacher_persona.name}，一位富有耐心的教师，"
                f"运用苏格拉底教学法帮助学生自主思考和探索知识。"
            )

        return f"""{persona}

【教学方法——苏格拉底式提问】
1. 绝不直接给出答案。通过一连串由浅入深的问题引导学习者自己发现答案。
2. 每次回复至少包含一个引导性问题，推动学习者思考下一步。
3. 当学习者的回答有误时，不要直接纠正；而是通过反问让他们重新审视自己的推理。
4. 适时总结学习者已经掌握的部分，再引向尚未理解的部分。
5. 保持专业、耐心、鼓励的态度。

【可视化工具——Mermaid 图表】
当概念关系、流程步骤、知识结构需要可视化时，可以在回复中使用 ```mermaid 代码块生成图表。
支持的图表类型：flowchart（流程图）、mindmap（思维导图）、sequenceDiagram（时序图）、classDiagram（类图）、graph（关系图）。
使用时机：解释复杂概念关系、展示解题步骤、梳理知识结构时。不要每次回复都画图，只在图表确实有助于理解时使用。"""

    def _build_dynamic_layer(
        self,
        relationship_instructions: str,
        relationship_stage: str,
        learner_profile: LearnerProfile | None,
        retrieved_memories: list[dict] | None,
        prev_emotion: dict | None,
        mastery_level: int = 50,
        knowledge_context: str = "",
    ) -> str:
        """Changes per turn: stage, scaffold, learner state, memories, knowledge graph."""
        parts: list[str] = []

        # 1. Relationship stage
        stage_text = self.STAGE_PROMPTS.get(relationship_stage, self.STAGE_PROMPTS["stranger"])
        parts.append(f"【当前关系阶段：{relationship_stage}】\n{stage_text}")
        if relationship_instructions:
            parts.append(f"【关系维度指令】\n{relationship_instructions}")

        # 2. Adaptive scaffold (Fuzzy Logic ZPD)
        emotion_type = prev_emotion.get("emotion_type", "neutral") if prev_emotion else "neutral"
        scaffold = self.compute_scaffold_level(emotion_type, mastery_level)
        scaffold_text = self.SCAFFOLD_INSTRUCTIONS[scaffold]
        parts.append(f"【学习者状态】情感: {emotion_type} | 知识掌握度: {mastery_level}/100\n{scaffold_text}")

        # 3. Learner profile
        profile_lines: list[str] = []
        if learner_profile:
            profile = learner_profile.profile if isinstance(learner_profile.profile, dict) else {}

            preferences = profile.get("preferences") if isinstance(profile, dict) else None
            if isinstance(preferences, dict):
                pairs = [f"{k}: {v}" for k, v in preferences.items() if v]
                if pairs:
                    profile_lines.append(f"学习偏好: {', '.join(pairs)}")

            affect = profile.get("affect") if isinstance(profile, dict) else None
            if isinstance(affect, dict):
                pairs = [f"{k}: {v}" for k, v in affect.items() if v]
                if pairs:
                    profile_lines.append(f"情感模式: {', '.join(pairs)}")

            metacognition = profile.get("metacognition") if isinstance(profile, dict) else None
            if isinstance(metacognition, dict):
                pairs = [f"{k}: {v}" for k, v in metacognition.items() if v]
                if pairs:
                    profile_lines.append(f"元认知特质: {', '.join(pairs)}")
        if profile_lines:
            parts.append("【学习者画像】\n" + "\n".join(profile_lines))

        # 4. Retrieved memories
        if retrieved_memories:
            mem_lines = [f"- {m['content']}" for m in retrieved_memories]
            parts.append("【相关学习记忆】\n" + "\n".join(mem_lines))

        # 5. Knowledge graph context
        if knowledge_context:
            parts.append("【学习者已掌握的知识关系】\n" + knowledge_context)

        return "\n\n".join(parts)

    def parse_tool_request(self, response: str) -> dict | None:
        """Parse tool request from LLM response"""
        # Try JSON format
        try:
            if '<tool>' in response or '</tool>' in response:
                # Extract content between tool tags
                match = re.search(r'<tool>(.*?)</tool>', response, re.DOTALL)
                if match:
                    tool_data = json.loads(match.group(1))
                    return tool_data
        except (json.JSONDecodeError, AttributeError):
            pass

        return None

    async def process_message(
        self,
        session_id: int,
        user_message: str,
        user_api_key: str = None,
        provider: str = "claude",
        db: Session | None = None,
    ) -> dict:
        """Process user message and generate teacher response"""
        own_db = False
        if db is None:
            db = SessionLocal()
            own_db = True

        try:
            # 1. Get session context
            session = db.query(SessionModel).filter(SessionModel.id == session_id).first()
            if not session:
                return {"type": "error", "reply": "会话不存在"}

            # 2. Get teacher persona
            teacher_persona = None
            if session.teacher_persona_id:
                teacher_persona = db.query(TeacherPersona).filter(
                    TeacherPersona.id == session.teacher_persona_id
                ).first()

            if not teacher_persona:
                fallback_name = "老师"
                if session.sage_character_id:
                    sage_character = db.query(Character).filter(
                        Character.id == session.sage_character_id
                    ).first()
                    if sage_character and sage_character.name:
                        fallback_name = sage_character.name
                teacher_persona = SimpleNamespace(
                    name=f"{fallback_name}导师",
                    system_prompt_template=None,
                )

            # 3. Get learner profile
            learner_profile = None
            if session.learner_profile_id:
                learner_profile = db.query(LearnerProfile).filter(
                    LearnerProfile.id == session.learner_profile_id
                ).first()

            # 4. Get checkpoint time for memory retrieval
            checkpoint_time = None
            if session.parent_checkpoint_id:
                checkpoint = db.query(Checkpoint).filter(
                    Checkpoint.id == session.parent_checkpoint_id
                ).first()
                checkpoint_time = checkpoint.created_at.isoformat() if checkpoint else None

            # 5. Retrieve relevant learning memories
            retrieved_memories: list[dict] = []
            retrieved_memories = self.knowledge.retrieve_memories(
                db=db,
                world_id=session.world_id,
                current_topic=user_message,
                checkpoint_time=checkpoint_time,
                limit=5
            )

            # 6. Get previous emotion from last user message (for dynamic prompt layer)
            prev_emotion = None
            last_user_msg = (
                db.query(ChatMessage)
                .filter(ChatMessage.session_id == session_id, ChatMessage.sender_type == "user")
                .order_by(ChatMessage.timestamp.desc())
                .first()
            )
            if last_user_msg and last_user_msg.emotion_analysis:
                prev_emotion = last_user_msg.emotion_analysis

            knowledge_graph = self.knowledge.get_knowledge(db, session.world_id)
            concept_mastery = [
                float(item.get("mastery", 0.0))
                for item in (knowledge_graph.get("concepts") or {}).values()
                if isinstance(item, dict) and isinstance(item.get("mastery"), (int, float))
            ]
            mastery_level = int(sum(concept_mastery) / len(concept_mastery) * 100) if concept_mastery else 50

            knowledge_context = self.knowledge.get_relevant_context(
                db,
                session.world_id,
                user_message,
                checkpoint_time=checkpoint_time,
                session_id=session.id,
            )
            relationship = session.relationship or _default_relationship()
            relationship_stage = relationship.get("stage", "stranger")
            relationship_instructions = self.relationship.get_instructions(
                relationship.get("dimensions", {})
            )

            # 5. Build dynamic system prompt (dual-layer architecture + ZPD scaffold)
            system_prompt = self.build_system_prompt(
                teacher_persona,
                relationship_stage,
                relationship_instructions,
                learner_profile,
                retrieved_memories,
                prev_emotion,
                mastery_level,
                knowledge_context,
            )

            # 6. Get recent chat history (limit to last 30 messages to control token usage)
            chat_history = (
                db.query(ChatMessage)
                .filter(ChatMessage.session_id == session_id)
                .order_by(ChatMessage.timestamp.desc())
                .limit(30)
                .all()
            )
            chat_history.reverse()  # restore chronological order

            # Convert to messages format for LLM
            messages = []
            for msg in chat_history:
                messages.append({
                    "role": self.ROLE_MAP.get(msg.sender_type, "user"),
                    "content": msg.content
                })

            # Add current message
            messages.append({"role": "user", "content": user_message})

            # 7. Call LLM
            llm_adapter = get_llm_adapter(provider)
            llm_response = await llm_adapter.chat(
                messages=messages,
                system_prompt=system_prompt,
                user_api_key=user_api_key
            )

            # 8. Parse tool request
            tool_request = self.parse_tool_request(llm_response)
            if tool_request:
                return {
                    "type": "tool_request",
                    "tool": tool_request.get("tool"),
                    "query": tool_request.get("query"),
                    "reason": tool_request.get("reason"),
                    "reply": llm_response
                }

            # 9. Analyze emotion (LLM-based when API key available, local fallback)
            emotion = await self.analyzer.analyze_emotion(user_message, user_api_key, provider)

            # 10. Update relationship dimensions/stage
            old_relationship = dict(session.relationship or _default_relationship())
            updated_relationship = self.relationship.update_dimensions(
                session,
                user_message,
                emotion,
                episode_type="chat",
            )
            session.relationship = updated_relationship
            new_stage = updated_relationship.get("stage", "stranger")
            old_stage = old_relationship.get("stage", "stranger")
            if new_stage != old_stage:
                # Record stage change
                stage_record = RelationshipStageRecord(
                    session_id=session_id,
                    stage=new_stage,
                    reason=f"关系维度更新触发阶段变化: {old_stage} -> {new_stage}"
                )
                db.add(stage_record)
            relationship_events = self.relationship.check_events(old_relationship, updated_relationship)

            # 11. Update knowledge graph and learner profile
            self.knowledge.update_after_chat(
                db,
                session.world_id,
                user_message,
                llm_response,
                emotion,
                session_id=session.id,
            )
            await self.analyzer.update_learner_profile(
                user_id=session.user_id,
                world_id=session.world_id,
                interaction={
                    "message": user_message,
                    "emotion_type": emotion.get("emotion_type"),
                    "confidence": emotion.get("confidence"),
                },
                db=db,
            )

            # 11.1 Update UserProfile (incremental update)
            from backend.services.user_profile import update_user_profile_after_chat
            update_user_profile_after_chat(db, session.user_id, session.world_id)

            # 12. Persist DB changes
            if own_db:
                db.commit()
            else:
                db.flush()

            # 13. Return response
            return {
                "type": "text",
                "reply": llm_response,
                "emotion": emotion,
                "relationship_stage": new_stage,
                "relationship": updated_relationship,
                "relationship_events": relationship_events,
                "used_memory_ids": []
            }

        except Exception:
            db.rollback()
            logger.error("Message processing failed", exc_info=True)
            return {
                "type": "error",
                "reply": "处理消息时出错，请重试"
            }
        finally:
            if own_db:
                db.close()


# Global instance
learning_engine = LearningEngine()
