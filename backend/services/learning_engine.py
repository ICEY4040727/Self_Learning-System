"""Learning Engine - Core logic for Socratic learning system

P1 #183 存储结构重设计 - 使用 MemoryFact 替代 Knowledge
"""

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
#
# 记忆系统 (MemoryFact):
#   - sage character 创建时，从 traveler character + learner_profile 生成 seed memory
#   - 每轮对话后，从 LLM 回复中提取 <memory> 标签，写入 memory_facts
#   - 提示词构建时，从 memory_facts 检索相关记忆注入上下文
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
    LearnerProfile,
    RelationshipStageRecord,
    TeacherPersona,
    _default_relationship,
)
from backend.models.models import (
    Session as SessionModel,
)
from backend.services.dynamic_analyzer import DynamicAnalyzer
from backend.services.llm.adapter import get_llm_adapter
from backend.services.memory_extractor import memory_extractor, should_extract_memory
from backend.services.memory_facts import memory_facts_service
from backend.services.prompt_builder import PromptBuilder, SceneConfig
from backend.services.relationship import relationship_service

logger = logging.getLogger(__name__)


class LearningEngine:
    """Learning engine for processing user messages and generating AI responses"""

    ROLE_MAP = {"user": "user", "teacher": "assistant"}

    def __init__(self):
        self.analyzer = DynamicAnalyzer()
        self.relationship = relationship_service
        # 模块化提示词构建器（已集成 MemoryFactsModule）
        self.prompt_builder = PromptBuilder(
            relationship_svc=self.relationship,
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

            # 4. Get traveler character (for seed memory and context)
            traveler_character = None
            if session.traveler_character_id:
                traveler_character = db.query(Character).filter(
                    Character.id == session.traveler_character_id
                ).first()

            # 5. Get previous emotion from last user message (DD13: prev_emotion bug fix)
            last_user_msg = (
                db.query(ChatMessage)
                .filter(ChatMessage.session_id == session_id, ChatMessage.sender_type == "user")
                .order_by(ChatMessage.timestamp.desc())
                .first()
            )
            prev_emotion = None
            if last_user_msg and last_user_msg.emotion_analysis:
                prev_emotion = last_user_msg.emotion_analysis

            # 6. Build system prompt using modular PromptBuilder
            # MemoryFactsModule 会自动从 memory_facts 检索相关记忆
            relationship = session.relationship or _default_relationship()
            relationship_stage = relationship.get("stage", "stranger")
            relationship_instructions = self.relationship.get_instructions(
                relationship.get("dimensions", {})
            )

            # 构建上下文（包含 character_id 给 MemoryFactsModule 使用）
            context = {
                "db": db,
                "world_id": session.world_id,
                "session_id": session.id,
                "course_id": session.course_id,
                "character_id": session.sage_character_id,  # 给 MemoryFactsModule 使用
                "relationship": {
                    "stage": relationship_stage,
                    "dimensions": relationship.get("dimensions", {}),
                    "instructions": relationship_instructions,
                },
                "learner_profile": learner_profile,
                "prev_emotion": prev_emotion,  # DD13: 使用实际的 emotion_analysis 值
                "mastery_level": 50,  # TODO: 从 FSRSState 计算
                "user_message": user_message,  # 用于记忆检索
            }

            system_prompt = self.prompt_builder.build(
                teacher_persona=teacher_persona,
                scene=SceneConfig.LEARNING,
                context=context,
                traveler_character=traveler_character,
            )

            # 7. Get recent chat history (limit to last 30 messages)
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

            # 8. Call LLM
            llm_adapter = get_llm_adapter(provider)
            llm_response = await llm_adapter.chat(
                messages=messages,
                system_prompt=system_prompt,
                user_api_key=user_api_key
            )

            # 9. Parse tool request
            tool_request = self.parse_tool_request(llm_response)
            if tool_request:
                return {
                    "type": "tool_request",
                    "tool": tool_request.get("tool"),
                    "query": tool_request.get("query"),
                    "reason": tool_request.get("reason"),
                    "reply": llm_response
                }

            # 10. Analyze emotion
            emotion = await self.analyzer.analyze_emotion(user_message, user_api_key, provider)

            # 11. Update relationship dimensions/stage
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
                stage_record = RelationshipStageRecord(
                    session_id=session_id,
                    stage=new_stage,
                    reason=f"关系维度更新触发阶段变化: {old_stage} -> {new_stage}"
                )
                db.add(stage_record)
            relationship_events = self.relationship.check_events(old_relationship, updated_relationship)

            # 12. Extract and save memories from LLM response
            used_memory_ids = []
            result = None
            if should_extract_memory(llm_response):
                result = memory_extractor.extract(llm_response)
                if result.memories:
                    # 保存 AI 回复消息
                    ai_message = (
                        db.query(ChatMessage)
                        .filter(ChatMessage.session_id == session_id, ChatMessage.sender_type == "assistant")
                        .order_by(ChatMessage.timestamp.desc())
                        .first()
                    )

                    # 写入记忆
                    memory_data = [{
                        "fact_type": m.fact_type,
                        "content": m.content,
                        "concept_tags": m.concept_tags,
                        "salience": m.salience,
                        "expires_at": m.expires_at,
                    } for m in result.memories]

                    used_memory_ids = memory_facts_service.write_memory_facts(
                        db=db,
                        character_id=session.sage_character_id,
                        world_id=session.world_id,
                        memories=memory_data,
                        source_message_id=ai_message.id if ai_message else None,
                    )

            # 13. Update learner profile
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

            # 14. Update UserProfile
            from backend.services.user_profile import update_user_profile_after_chat
            update_user_profile_after_chat(db, session.user_id, session.world_id)

            # 15. Persist DB changes
            if own_db:
                db.commit()
            else:
                db.flush()

            # 16. Return response (移除 <memory> 标签)
            clean_response = memory_extractor.strip_tags(llm_response)

            # 计算本次提取的 memory 数量 (Issue #192)
            memory_extracted_count = len(result.memories) if result and result.memories else 0

            return {
                "type": "text",
                "reply": clean_response,
                "emotion": emotion,
                "relationship_stage": new_stage,
                "relationship": updated_relationship,
                "relationship_events": relationship_events,
                "used_memory_ids": used_memory_ids,
                "memory_extracted_count": memory_extracted_count,  # Issue #192
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

    async def create_seed_memories(
        self,
        db: Session,
        sage_character_id: int,
        traveler_character: Character,
        learner_profile: LearnerProfile | None = None,
    ) -> list[int]:
        """
        为 sage character 创建 seed memories

        从 traveler character 和 learner_profile 提取初始认知事实。
        """
        return memory_facts_service.create_seed_memories(
            db=db,
            sage_character_id=sage_character_id,
            traveler_character=traveler_character,
            learner_profile=learner_profile,
        )


# Global instance
learning_engine = LearningEngine()
