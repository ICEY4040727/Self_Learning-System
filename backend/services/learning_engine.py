"""Learning Engine - Core logic for Socratic learning system"""

import json
import re
from typing import List, Optional
from backend.services.llm.adapter import get_llm_adapter
from backend.services.memory import memory_service
from backend.services.dynamic_analyzer import DynamicAnalyzer
from backend.db.database import SessionLocal
from backend.models.models import (
    Session as SessionModel,
    TeacherPersona,
    LearnerProfile,
    ChatMessage,
    RelationshipStageRecord
)


class LearningEngine:
    """Learning engine for processing user messages and generating AI responses"""

    def __init__(self):
        self.memory = memory_service
        self.analyzer = DynamicAnalyzer()

    def get_relationship_stage_prompt(self, stage: str) -> str:
        """Get prompt adaptation based on relationship stage"""
        stage_prompts = {
            "stranger": "以温和、耐心的方式自我介绍，建立信任。使用简单易懂的语言，避免过于专业术语。",
            "acquaintance": "开始更多互动，逐步了解学习者的背景和需求。保持友好但适当的距离。",
            "friend": "以朋友的方式交流，可以更加轻松随意。分享学习方法，适度关心学习者的状态。",
            "mentor": "提供专业、深入的指导。鼓励学习者挑战更高难度，分享专业知识见解。",
            "partner": "深入讨论知识话题，共同探索。认可学习者的成长，可以进行更深层次的学术交流。"
        }
        return stage_prompts.get(stage, stage_prompts["stranger"])

    def build_system_prompt(
        self,
        teacher_persona: TeacherPersona,
        relationship_stage: str,
        learner_profile: Optional[LearnerProfile] = None,
        retrieved_memories: List[dict] = None
    ) -> str:
        """Build dynamic system prompt based on teacher persona, relationship stage, and memories"""

        # 1. Base prompt from teacher persona
        base_prompt = teacher_persona.system_prompt_template or ""
        if not base_prompt:
            base_prompt = f"你是 {teacher_persona.name}，一位富有耐心的教师，运用苏格拉底教学法帮助学生自主思考和探索知识。"

        # 2. Add relationship stage adaptation
        stage_prompt = self.get_relationship_stage_prompt(relationship_stage)

        # 3. Add learner profile context
        learner_context = ""
        if learner_profile:
            if learner_profile.learning_style:
                learning_style = learner_profile.learning_style
                if isinstance(learning_style, dict):
                    style_text = ", ".join([f"{k}: {v}" for k, v in learning_style.items() if v])
                    learner_context += f"\n学习者风格偏好: {style_text}"

            if learner_profile.cognitive_traits:
                cognitive = learner_profile.cognitive_traits
                if isinstance(cognitive, dict):
                    traits_text = ", ".join([f"{k}: {v}" for k, v in cognitive.items() if v])
                    learner_context += f"\n学习者认知特质: {traits_text}"

        # 4. Add retrieved memories
        memory_context = ""
        if retrieved_memories:
            memory_context = "\n\n相关学习记忆:"
            for mem in retrieved_memories:
                memory_context += f"\n- {mem['content']}"

        # Combine all parts
        system_prompt = f"""{base_prompt}

{stage_prompt}
{learner_context}
{memory_context}

请用苏格拉底式提问法引导学习者思考，通过提问而不是直接给出答案来帮助他们理解。
保持专业、耐心、鼓励的态度。
"""

        return system_prompt

    def parse_tool_request(self, response: str) -> Optional[dict]:
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
        provider: str = "claude"
    ) -> dict:
        """Process user message and generate teacher response"""
        db = SessionLocal()

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
                return {"type": "error", "reply": "未配置教师人格"}

            # 3. Get learner profile
            learner_profile = None
            if session.learner_profile_id:
                learner_profile = db.query(LearnerProfile).filter(
                    LearnerProfile.id == session.learner_profile_id
                ).first()

            # 4. Retrieve relevant memories
            retrieved_memories = self.memory.retrieve(
                str(session_id),
                user_message,
                top_k=3
            )

            # 5. Build dynamic system prompt
            system_prompt = self.build_system_prompt(
                teacher_persona,
                session.relationship_stage or "stranger",
                learner_profile,
                retrieved_memories
            )

            # 6. Get chat history for context
            chat_history = db.query(ChatMessage).filter(
                ChatMessage.session_id == session_id
            ).order_by(ChatMessage.timestamp).all()

            # Convert to messages format for LLM
            messages = []
            for msg in chat_history:
                messages.append({
                    "role": msg.sender_type,
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

            # 9. Analyze emotion
            emotion = await self.analyzer.analyze_emotion(user_message)

            # 10. Update relationship stage
            new_stage = await self.analyzer.update_relationship_stage(session_id, emotion, db)
            if new_stage != session.relationship_stage:
                session.relationship_stage = new_stage
                # Record stage change
                stage_record = RelationshipStageRecord(
                    session_id=session_id,
                    stage=new_stage,
                    reason=f"情感分析: {emotion['emotion_type']}, 消息数: {len(chat_history)}"
                )
                db.add(stage_record)

            # 11. Store user message in memory
            user_memory_id = self.memory.add_memory(
                str(session_id),
                f"学习者: {user_message}",
                {"type": "user", "emotion": emotion["emotion_type"]}
            )

            # 12. Store teacher response in memory
            teacher_memory_id = self.memory.add_memory(
                str(session_id),
                f"教师: {llm_response}",
                {"type": "teacher"}
            )

            # 13. Update chat message with emotion analysis
            db.commit()

            # 14. Return response
            return {
                "type": "text",
                "reply": llm_response,
                "emotion": emotion,
                "relationship_stage": session.relationship_stage,
                "used_memory_ids": [user_memory_id, teacher_memory_id]
            }

        except Exception as e:
            return {
                "type": "error",
                "reply": f"处理消息时出错: {str(e)}"
            }
        finally:
            db.close()


# Global instance
learning_engine = LearningEngine()