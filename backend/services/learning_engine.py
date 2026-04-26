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

from backend.models.models import (
    Character,
    ChatMessage,
    LearnerProfile,
    RelationshipStageRecord,
    _default_relationship,
)
from backend.models.models import (
    Session as SessionModel,
)
from backend.services.dynamic_analyzer import DynamicAnalyzer
from backend.services.gamification import gamification_engine
from backend.services.llm.adapter import get_llm_adapter
from backend.services.mastery_tracker import mastery_tracker
from backend.services.memory_extractor import memory_extractor
from backend.services.memory_facts import memory_facts_service
from backend.services.memory_manager import memory_manager
from backend.services.narrative_engine import narrative_engine
from backend.services.profile_aggregator import profile_aggregator
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
        db: Session,
        user_api_key: str = None,
        provider: str = "claude",
    ) -> dict:
        """Process user message and generate teacher response"""

        try:
            # 1. Get session context
            session = db.query(SessionModel).filter(SessionModel.id == session_id).first()
            if not session:
                return {"type": "error", "reply": "会话不存在"}

            # 2. Get sage character (Phase 1.5 DD1: 主要角色来源)
            sage_character = None
            if session.sage_character_id:
                sage_character = db.query(Character).filter(
                    Character.id == session.sage_character_id
                ).first()

            # Phase 1.5 DD1: teacher_persona_id 不再用于查询，仅保留用于兼容旧数据

            # 4. Get learner profile
            learner_profile = None
            if session.learner_profile_id:
                learner_profile = db.query(LearnerProfile).filter(
                    LearnerProfile.id == session.learner_profile_id
                ).first()

            # 5. Get traveler character (for seed memory and context)
            traveler_character = None
            if session.traveler_character_id:
                traveler_character = db.query(Character).filter(
                    Character.id == session.traveler_character_id
                ).first()

            # 6. Get previous emotion from last user message (DD13: prev_emotion bug fix)
            last_user_msg = (
                db.query(ChatMessage)
                .filter(ChatMessage.session_id == session_id, ChatMessage.sender_type == "user")
                .order_by(ChatMessage.timestamp.desc())
                .first()
            )
            prev_emotion = None
            if last_user_msg and last_user_msg.emotion_analysis:
                prev_emotion = last_user_msg.emotion_analysis

            # 7. Build system prompt using modular PromptBuilder
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

            # Phase 1.5 DD1: 使用 sage_character 替代 teacher_persona
            system_prompt = self.prompt_builder.build(
                character=sage_character,
                scene=SceneConfig.LEARNING,
                context=context,
                traveler_character=traveler_character,
            )

            # 8. Get chat history via MemoryManager (Token-aware budget)
            messages = memory_manager.get_working_context(db, session_id)

            # Add current message
            messages.append({"role": "user", "content": user_message})

            # 9. Call LLM
            llm_adapter = get_llm_adapter(provider)
            llm_response = await llm_adapter.chat(
                messages=messages,
                system_prompt=system_prompt,
                user_api_key=user_api_key
            )

            # 10. Parse tool request
            tool_request = self.parse_tool_request(llm_response)
            if tool_request:
                return {
                    "type": "tool_request",
                    "tool": tool_request.get("tool"),
                    "query": tool_request.get("query"),
                    "reason": tool_request.get("reason"),
                    "reply": llm_response
                }

            # 11. Analyze emotion
            emotion = await self.analyzer.analyze_emotion(user_message, user_api_key, provider)

            # 12. Update relationship dimensions/stage
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

            # 13. Extract and save memories via MemoryManager (dual-channel)
            used_memory_ids = []
            result = memory_manager.extract_and_store(
                db,
                llm_response,
                user_message,
                character_id=session.sage_character_id,
                world_id=session.world_id,
            )
            if result and result.memories:
                used_memory_ids = [m.fact_type for m in result.memories]

            # 14. Update learner profile
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

            # 15. Run ProfileAggregator (dimension_scores, learning_stats)
            profile_aggregator.aggregate(
                db,
                character_id=session.sage_character_id,
                world_id=session.world_id,
                user_id=session.user_id,
            )

            # 15.5 Evolve salience moved to scheduled daily job (services/scheduler.py)
            # — running it per-message decayed every memory by a full day's worth on
            # each chat (max(days, 1.0) floor). Daily cron keeps semantics correct
            # and removes the O(N) scan from the request path.

            # 16. Update UserProfile
            from backend.services.user_profile import update_user_profile_after_chat
            update_user_profile_after_chat(db, session.user_id, session.world_id)

            # 17. Persist DB changes
            db.flush()

            # 17.5 Prepare recent facts for downstream observers
            recent_facts = result.memories if result else []

            # 17.6 Mastery tracking: MemoryFact → 概念掌握度 → 自适应推进 (Phase 3 Step 4)
            mastery_result = mastery_tracker.update_from_memories(
                db=db,
                memories=recent_facts,
                course_id=session.course_id,
                world_id=session.world_id,
            )

            # 18. Narrative events (观察者，不调 LLM)
            narrative_events = narrative_engine.check_triggers(
                db,
                user_id=session.user_id,
                character_id=session.sage_character_id,
                world_id=session.world_id,
                recent_facts=recent_facts,
                current_stage=new_stage,
                prev_stage=old_stage,
            )

            # 19. Achievement check (观察者，不调 LLM)
            lp = db.query(LearnerProfile).filter(
                LearnerProfile.user_id == session.user_id,
                LearnerProfile.world_id == session.world_id,
            ).first()
            dim_scores = {}
            learn_stats = {}
            if lp and lp.profile:
                dim_scores = lp.profile.get("dimension_scores", {})
                learn_stats = lp.profile.get("learning_stats", {})

            new_achievements = gamification_engine.check_achievements(
                db,
                user_id=session.user_id,
                character_id=session.sage_character_id,
                world_id=session.world_id,
                stats=learn_stats,
                dimension_scores=dim_scores,
                current_stage=new_stage,
                recent_facts=recent_facts,
            )

            # 20. Return response (移除 <memory> 标签)
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
                "narrative_events": narrative_events,
                "new_achievements": new_achievements,
            }

        except Exception:
            db.rollback()
            logger.error("Message processing failed", exc_info=True)
            return {
                "type": "error",
                "reply": "处理消息时出错，请重试"
            }

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
