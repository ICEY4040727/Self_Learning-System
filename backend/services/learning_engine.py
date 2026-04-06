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
from backend.services.prompt_builder import PromptBuilder, SceneConfig

logger = logging.getLogger(__name__)


class LearningEngine:
    """Learning engine for processing user messages and generating AI responses"""

    ROLE_MAP = {"user": "user", "teacher": "assistant"}

    def __init__(self):
        self.analyzer = DynamicAnalyzer()
        self.knowledge = knowledge_service
        self.relationship = relationship_service
        # 模块化提示词构建器
        self.prompt_builder = PromptBuilder(
            knowledge_svc=self.knowledge,
            relationship_svc=self.relationship,
        )

    # ------------------------------------------------------------------
    # 新版提示词构建方法（使用模块化 PromptBuilder）
    # ------------------------------------------------------------------
    def build_system_prompt_v2(
        self,
        teacher_persona: TeacherPersona,
        relationship_stage: str,
        relationship_instructions: str = "",
        learner_profile: LearnerProfile | None = None,
        prev_emotion: dict | None = None,
        mastery_level: int = 50,
        knowledge_context: str = "",
        db: Session | None = None,
        world_id: int | None = None,
        session_id: int | None = None,
        traveler_character=None,
    ) -> str:
        """
        使用模块化 PromptBuilder 构建系统提示词
        
        Args:
            teacher_persona: 教师人格
            relationship_stage: 关系阶段
            relationship_instructions: 关系维度指令
            learner_profile: 学习者画像
            prev_emotion: 上一轮情感
            mastery_level: 掌握度
            knowledge_context: 知识上下文
            db: 数据库会话
            world_id: 世界ID
            session_id: 会话ID
            traveler_character: 旅人角色
        """
        # 构建上下文
        context = {
            "db": db,
            "world_id": world_id,
            "session_id": session_id,
            "relationship": {
                "stage": relationship_stage,
                "dimensions": {},
                "instructions": relationship_instructions,
            },
            "learner_profile": learner_profile,
            "prev_emotion": prev_emotion,
            "mastery_level": mastery_level,
            "knowledge_context": knowledge_context,
        }
        
        return self.prompt_builder.build(
            teacher_persona=teacher_persona,
            scene=SceneConfig.LEARNING,
            context=context,
            traveler_character=traveler_character,
        )

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

            # 5. Build system prompt using modular PromptBuilder
            system_prompt = self.build_system_prompt_v2(
                teacher_persona,
                relationship_stage,
                relationship_instructions,
                learner_profile,
                prev_emotion,
                mastery_level,
                knowledge_context,
                db=db,
                world_id=session.world_id,
                session_id=session.id,
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
