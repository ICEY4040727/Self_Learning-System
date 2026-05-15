from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from backend.api.routes.auth import get_current_user
from backend.db.database import get_db
from backend.models.models import (
    Character,
    ChatMessage,
    Course,
    LearnerProfile,
    # Phase 1.5 DD1: TeacherPersona 已删除，相关功能合并到 Character
    User,
    World,
    WorldCharacter,
    _default_relationship,
)
from backend.models.models import (
    CourseProgress,
    LessonPlan,
    MemoryFact,
    Session as SessionModel,
)
from backend.services.learning_engine import learning_engine
from backend.services.character_llm_settings import get_effective_character_llm_config

router = APIRouter()


# Chat Request/Response models
class StartRequest(BaseModel):
    """Optional body for start endpoint — allows specifying which sage to use."""
    sage_id: int | None = None


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=5000)


class ChatResponse(BaseModel):
    type: str  # text, tool_request, choice
    reply: str
    choices: list[str] | None = None
    emotion: dict | None = None
    relationship_stage: str | None = None
    relationship: dict | None = None
    relationship_events: list[dict] | None = None
    expression_hint: str | None = None  # "happy", "thinking", "concerned", "default"
    # Issue #192: 本次会话提取的记忆数量
    memory_extracted_count: int = 0
    # Phase 3: 叙事事件 & 成就
    narrative_events: list[dict] | None = None
    new_achievements: list[dict] | None = None


EXPRESSION_MAP = {
    "curiosity": "thinking",
    "confusion": "concerned",
    "frustration": "concerned",
    "excitement": "happy",
    "satisfaction": "happy",
    "boredom": "default",
    "anxiety": "concerned",
    "neutral": "default",
}


# ── 静态 greeting 保留为 fallback ────────────────────────────────────────
_GREETING_FALLBACKS = {
    "stranger": "你好，我是{name}。很高兴认识你！今天想学点什么呢？",
    "acquaintance": "嗨，又见面了。今天想继续上次的话题吗？",
    "friend": "来了来了！今天状态怎么样？",
    "mentor": "准备好挑战更深的问题了吗？",
    "partner": "老朋友，我们继续探索吧。",
}


def _fallback_greeting(stage: str, persona_name: str | None) -> str:
    template = _GREETING_FALLBACKS.get(stage, _GREETING_FALLBACKS["stranger"])
    return template.format(name=persona_name or "老师")


# ── 动态 greeting: LLM 生成课程感知的开场白 ────────────────────────────────

_GREETING_SYSTEM_PROMPT = """你是一位导师，正在对面前唯一的学生说开场白。

严格规则：
- 这是1对1教学，不要说"大家好""同学们"，直接像对朋友说话一样
- 直接输出开场白（1-3句话），不要输出任何思考过程、分析、解释
- 语气要与「关系阶段」匹配（stranger=友好但得体，friend=轻松随意）
- 自然融入要学的知识点，不要生硬罗列
- 如果学生有薄弱点，温和地提一句鼓励
- 如果是第一节课，简短介绍自己并欢迎
- 用中文，口语化，自然

正确示例：你好，我是xxx。欢迎来到博弈论——今天我们会从最基本的概念聊起，了解一下什么是"策略思维"。
错误示例：大家好，我是xxx...
错误示例：让我想想...（不要输出思考过程）"""


async def _generate_contextual_greeting(
    db: Session,
    course: Course,
    sage_character,
    stage: str,
    current_user: User,
    sage_world_link=None,
    traveler_world_link=None,
) -> str | None:
    """基于课程进度、章节内容、学生掌握度，调用 LLM 生成开场白。

    返回 None 表示 LLM 不可用（由调用方 fallback 到静态模板）。
    """
    # 1) 收集上下文信号
    course_id = course.id
    sage_name = sage_character.name if sage_character else "老师"

    # 当前章节
    current_lesson = None
    total_lessons = 0
    lesson_index = 0
    completed_count = 0
    progress = db.query(CourseProgress).filter(
        CourseProgress.course_id == course_id,
        CourseProgress.user_id == current_user.id,
    ).first()
    if progress:
        lesson_index = progress.current_lesson_index or 0
        completed_count = len(progress.completed_lesson_ids or [])

    lessons = db.query(LessonPlan).filter(
        LessonPlan.course_id == course_id,
    ).order_by(LessonPlan.order_index).all()
    total_lessons = len(lessons)
    if lessons and 0 <= lesson_index < total_lessons:
        current_lesson = lessons[lesson_index]

    # 薄弱概念
    weak_concepts: list[str] = []
    if current_lesson and current_lesson.concepts:
        struggle_rows = db.query(MemoryFact).filter(
            MemoryFact.world_id == course.world_id,
            MemoryFact.subject_id == current_user.id,
            MemoryFact.fact_type == "concept_struggle",
        ).all()
        struggled = {s.content for s in struggle_rows if s.content}
        weak_concepts = [c for c in current_lesson.concepts if c in struggled]

    # 最近一次对话话题（取最近 3 条 teacher 消息的摘要）
    recent_topics = ""
    last_session = db.query(SessionModel).filter(
        SessionModel.course_id == course_id,
        SessionModel.user_id == current_user.id,
        SessionModel.ended_at != None,  # noqa: E711
    ).order_by(SessionModel.ended_at.desc()).first()
    if last_session:
        last_msgs = db.query(ChatMessage).filter(
            ChatMessage.session_id == last_session.id,
            ChatMessage.sender_type == "teacher",
        ).order_by(ChatMessage.timestamp.desc()).limit(3).all()
        if last_msgs:
            snippets = [m.content[:80] for m in reversed(last_msgs) if m.content]
            recent_topics = "\n".join(f"- {s}…" for s in snippets)

    # 2) 拼装 user prompt
    parts = [
        f"老师名字: {sage_name}",
        f"课程名称: {course.name}",
        f"关系阶段: {stage}",
    ]
    if sage_world_link:
        if getattr(sage_world_link, "world_title", None):
            parts.append(f"世界内身份: {sage_world_link.world_title}")
        if getattr(sage_world_link, "world_background", None):
            parts.append(f"世界背景: {sage_world_link.world_background}")
        if getattr(sage_world_link, "relationship_seed", None):
            parts.append(f"相识前提: {sage_world_link.relationship_seed}")
    if traveler_world_link:
        if getattr(traveler_world_link, "world_title", None):
            parts.append(f"学习者世界身份: {traveler_world_link.world_title}")
        if getattr(traveler_world_link, "world_background", None):
            parts.append(f"学习者世界背景: {traveler_world_link.world_background}")
    if current_lesson:
        parts.append(f"当前章节: {current_lesson.title}")
        if current_lesson.concepts:
            parts.append(f"本节概念: {', '.join(current_lesson.concepts)}")
        parts.append(f"课程进度: 第 {lesson_index + 1}/{total_lessons} 课（已完成 {completed_count} 课）")
    else:
        parts.append("这是课程的第一节课，还没有生成章节。")

    if weak_concepts:
        parts.append(f"学生薄弱点: {', '.join(weak_concepts)}")

    if recent_topics:
        parts.append(f"上次上课话题摘要:\n{recent_topics}")

    user_prompt = "\n".join(parts)

    # 3) 调用 LLM（轻量、短输出）
    try:
        config = get_effective_character_llm_config(current_user, sage_character)

        from backend.services.llm.providers import provider_needs_api_key
        if provider_needs_api_key(config.provider) and not config.api_key:
            return None

        from backend.services.llm.manager import get_llm_manager
        adapter = get_llm_manager().get_adapter(
            provider=config.provider,
            model=config.model,
            api_key=config.api_key,
            base_url=config.base_url,
        )
        response = await adapter.chat(
            messages=[{"role": "user", "content": user_prompt}],
            system_prompt=_GREETING_SYSTEM_PROMPT,
            user_api_key=config.api_key,
            temperature=config.temperature,
            max_tokens=min(config.max_tokens, 200),
        )
        # 清理 LLM 可能输出的思考过程
        import re as _re
        text = response
        # 移除 <think...</think > 标签（DeepSeek R1 等）
        text = _re.sub(r'<think[\s\S]*?</think\s*>', '', text, flags=_re.IGNORECASE)
        text = text.strip().strip('"').strip("'").strip()
        # 如果首行看起来像分析过程，跳过它取实际内容
        first_line = text.split('\n', 1)[0] if '\n' in text else text
        if any(first_line.startswith(p) for p in ('知者', '让我', '我需要', '分析', '思考', '根据')):
            rest = text.split('\n', 1)[1] if '\n' in text else ''
            rest = rest.strip()
            if rest:
                text = rest
        return text if text else None
    except Exception:
        import logging
        logging.getLogger(__name__).debug("dynamic greeting LLM call failed, will fallback", exc_info=True)
        return None



# ---------------------------------------------------------------------------
# Issue #212 helpers: extract duplicated patterns
# ---------------------------------------------------------------------------

def _get_active_session(db: Session, course_id: int, user_id: int):
    """Return the most recent active (un-ended) session for a course + user, or None."""
    return db.query(SessionModel).filter(
        SessionModel.course_id == course_id,
        SessionModel.user_id == user_id,
        SessionModel.ended_at == None,  # noqa: E711
    ).order_by(SessionModel.started_at.desc()).first()


def _get_session_characters(db: Session, session_obj):
    """Resolve sage/traveler Character objects from a Session's character ids.

    Returns (sage_character, traveler_character).
    Phase 1.5 DD1: 不再使用 TeacherPersona，直接从 Character 表获取人格数据。
    """
    sage_character = None
    traveler_character = None

    # 优先使用 sage_character_id (Phase 1.5 DD1 新字段)
    if getattr(session_obj, "sage_character_id", None):
        sage_character = db.query(Character).filter(
            Character.id == session_obj.sage_character_id
        ).first()

    # Fallback: 从 teacher_persona_id 兼容旧数据 (Session 可能仍存储旧数据)
    if not sage_character and getattr(session_obj, "teacher_persona_id", None):
        # teacher_persona_id 保留用于向后兼容，不再查询 TeacherPersona 表
        # 直接通过 character_id 查找对应的 Character
        from backend.models.models import WorldCharacter
        wc = db.query(WorldCharacter).filter(
            WorldCharacter.id == session_obj.teacher_persona_id
        ).first()
        if wc:
            sage_character = db.query(Character).filter(
                Character.id == wc.character_id
            ).first()

    if getattr(session_obj, "traveler_character_id", None):
        traveler_character = db.query(Character).filter(
            Character.id == session_obj.traveler_character_id
        ).first()

    return sage_character, traveler_character


def _get_world_character_link(db: Session, world_id: int, character_id: int, role: str | None = None):
    """Resolve a world-character binding for a specific world + character."""
    query = db.query(WorldCharacter).filter(
        WorldCharacter.world_id == world_id,
        WorldCharacter.character_id == character_id,
    )
    if role:
        query = query.filter(WorldCharacter.role == role)
    return query.first()


async def _build_start_response(
    session_id: int,
    course: Course,
    sage_character,
    traveler_character,
    relationship: dict,
    stage: str,
    sage_world_link=None,
    traveler_world_link=None,
    db: Session = None,
    current_user: User = None,
    is_new: bool = True,
    ):
    """Build the standard response dict for start/resume session endpoints.

    Uses LLM-generated contextual greeting when possible, falls back to
    static templates when LLM is unavailable.
    """
    # 1) 优先使用世界绑定的 greeting，再降级到角色全局 greeting
    world_greeting = sage_world_link.world_greeting if sage_world_link and sage_world_link.world_greeting else None
    custom_greeting = sage_character.greeting if sage_character and sage_character.greeting else None

    # 2) 尝试 LLM 动态生成课程感知 greeting（失败不影响主流程）
    dynamic_greeting = None
    if db and current_user:
        try:
            dynamic_greeting = await _generate_contextual_greeting(
                db=db,
                course=course,
                sage_character=sage_character,
                stage=stage,
                current_user=current_user,
                sage_world_link=sage_world_link,
                traveler_world_link=traveler_world_link,
            )
        except Exception:
            import logging as _l
            _l.getLogger(__name__).warning("dynamic greeting generation failed, using fallback", exc_info=True)

    # 3) Fallback 到静态模板（始终有效）
    fallback = _fallback_greeting(stage, sage_character.name if sage_character else None)

    # 优先级: world greeting → 角色 greeting → LLM 动态 → 静态模板
    greeting = world_greeting or custom_greeting or dynamic_greeting or fallback
    # 兜底：确保 greeting 永远不为空
    if not greeting:
        greeting = f"你好，我是{sage_character.name if sage_character else '老师'}。今天我们开始学习吧。"

    # Debug: log which greeting source was used
    import logging as _log
    _log.getLogger(__name__).info(
        "greeting sources: world=%r, custom=%r, dynamic=%r, fallback=%r → final=%r",
        world_greeting[:50] if world_greeting else None,
        custom_greeting[:50] if custom_greeting else None,
        dynamic_greeting[:50] if dynamic_greeting else None,
        fallback[:50] if fallback else None,
        greeting[:50] if greeting else None,
    )

    scenes = dict(course.world.scenes or {}) if course.world and course.world.scenes else {}
    background_picture = scenes.get("background_picture") or scenes.get("background")
    if background_picture:
        scenes["background_picture"] = background_picture
        scenes.setdefault("background", background_picture)

    return {
        "session_id": session_id,
        "is_new": is_new,
        "teacher_persona": sage_character.name if sage_character else None,
        "course": course.name,
        "relationship_stage": stage,
        "relationship": relationship,
        "greeting": greeting,
        "scenes": scenes,
        "sage": {
            "id": sage_character.id if sage_character else None,
            "name": sage_character.name if sage_character else None,
            "title": sage_character.title if sage_character else None,
            "symbol": (sage_character.tags[0] if isinstance(sage_character.tags, list) and sage_character.tags else sage_character.tags) if sage_character and sage_character.tags else None,
            "avatar": sage_character.avatar if sage_character else None,
            "sprites": sage_character.sprites if sage_character else None,
        } if sage_character else None,
        "sage_sprites": sage_character.sprites if sage_character else None,
        "traveler_sprites": traveler_character.sprites if traveler_character else None,
    }


# Start learning session
@router.post("/courses/{course_id}/start")
async def start_learning(
    course_id: int,
    body: StartRequest | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    import logging as _logging
    _logger = _logging.getLogger(__name__)
    _logger.warning("DEBUG start_learning called: course_id=%s, body=%r", course_id, body)

    course = db.query(Course).join(World, Course.world_id == World.id).filter(
        Course.id == course_id,
        World.user_id == current_user.id,
    ).first()
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")

    # 优先使用前端显式传入的 sage_id；否则回退到课程 meta / 世界主 sage
    explicit_sage_id = body.sage_id if body else None
    requested_sage_id = explicit_sage_id

    # Reuse existing active session — BUT only if sage matches or no sage specified
    existing = _get_active_session(db, course_id, current_user.id)

    if existing:
        # 如果指定了 sage_id 但和已有 session 的 sage 不同 → 结束旧 session，创建新的
        if requested_sage_id and existing.sage_character_id != requested_sage_id:
            existing.ended_at = datetime.now(UTC)
            db.commit()
            existing = None  # fall through to create new session

    if existing:
        sage_character, traveler_character = _get_session_characters(db, existing)
        sage_link = _get_world_character_link(db, course.world_id, existing.sage_character_id, "sage") if existing.sage_character_id else None
        traveler_link = _get_world_character_link(db, course.world_id, existing.traveler_character_id, "traveler") if existing.traveler_character_id else None
        relationship = existing.relationship or _default_relationship()
        stage = relationship.get("stage", "stranger")
        return await _build_start_response(
            session_id=existing.id,
            course=course,
            sage_character=sage_character,
            traveler_character=traveler_character,
            sage_world_link=sage_link,
            traveler_world_link=traveler_link,
            relationship=relationship,
            stage=stage,
            db=db,
            current_user=current_user,
            is_new=False,
        )

    # ── 创建新 session ──
    # 若前端未显式指定 sage_id，则优先用课程 meta 里的 sage_ids，再回退到世界主 sage
    if not requested_sage_id:
        meta_sage_ids = course.meta.get("sage_ids", []) if course.meta else []
        if meta_sage_ids:
            requested_sage_id = meta_sage_ids[0]
        else:
            primary_sage_link = db.query(WorldCharacter).filter(
                WorldCharacter.world_id == course.world_id,
                WorldCharacter.role == "sage",
            ).order_by(WorldCharacter.is_primary.desc(), WorldCharacter.id.asc()).first()
            requested_sage_id = primary_sage_link.character_id if primary_sage_link else None

    # 清理该 course 下可能残留的 active session（race condition 防护）
    stale = db.query(SessionModel).filter(
        SessionModel.course_id == course_id,
        SessionModel.user_id == current_user.id,
        SessionModel.ended_at == None,  # noqa: E711
    ).all()
    for s in stale:
        s.ended_at = datetime.now(UTC)
    if stale:
        db.commit()

    sage_link = None
    if requested_sage_id:
        sage_link = db.query(WorldCharacter).filter(
            WorldCharacter.world_id == course.world_id,
            WorldCharacter.character_id == requested_sage_id,
            WorldCharacter.role == "sage",
        ).first()
        if not sage_link and explicit_sage_id is not None:
            raise HTTPException(
                status_code=404,
                detail=f"Sage character {requested_sage_id} not found in this world",
            )
        if not sage_link:
            requested_sage_id = None
    traveler_link = db.query(WorldCharacter).filter(
        WorldCharacter.world_id == course.world_id,
        WorldCharacter.role == "traveler",
    ).order_by(WorldCharacter.is_primary.desc(), WorldCharacter.id.asc()).first()

    sage_character_id = sage_link.character_id if sage_link else None
    traveler_character_id = traveler_link.character_id if traveler_link else None

    # Phase 1.5 DD1: 直接从 Character 获取人格数据，不再查询 TeacherPersona
    sage_character = db.query(Character).filter(Character.id == sage_character_id).first() if sage_character_id else None

    # Get learner profile for this world
    learner_profile = db.query(LearnerProfile).filter(
        LearnerProfile.user_id == current_user.id,
        LearnerProfile.world_id == course.world_id,
    ).first()

    # Create new session
    traveler_character = db.query(Character).filter(Character.id == traveler_character_id).first() if traveler_character_id else None

    db_session = SessionModel(
        course_id=course_id,
        user_id=current_user.id,
        world_id=course.world_id,
        sage_character_id=sage_character_id,
        traveler_character_id=traveler_character_id,
        relationship=_default_relationship(),
        # Phase 1.5 DD1: system_prompt 直接从 Character.system_prompt_template 获取
        system_prompt=sage_character.system_prompt_template if sage_character else None,
        # teacher_persona_id 保留用于向后兼容，不再设置
        learner_profile_id=learner_profile.id if learner_profile else None,
    )
    db.add(db_session)
    db.commit()
    db.refresh(db_session)

    # Create seed memories for first session (P1 #183)
    # Seed from traveler character + learner_profile to sage character
    if sage_character_id and traveler_character:
        await learning_engine.create_seed_memories(
            db=db,
            sage_character_id=sage_character_id,
            traveler_character=traveler_character,
            traveler_world_link=traveler_link,
            learner_profile=learner_profile,
        )

    # sage_character & traveler_character already resolved above; SQLAlchemy
    # identity map keeps them attached after commit.

    return await _build_start_response(
        session_id=db_session.id,
        course=course,
        sage_character=sage_character,
        traveler_character=traveler_character,
        sage_world_link=sage_link,
        traveler_world_link=traveler_link,
        relationship=db_session.relationship,
        stage="stranger",
        db=db,
        current_user=current_user,
    )


# Send chat message
@router.post("/courses/{course_id}/chat", response_model=ChatResponse)
async def send_message(
    course_id: int,
    chat_request: ChatRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # Get active session for this course (reuse helper)
    db_session = _get_active_session(db, course_id, current_user.id)

    if not db_session:
        raise HTTPException(
            status_code=400,
            detail="No active session. Please call POST /courses/{course_id}/start with a sage_id first.",
        )

    sage_character, _traveler_character = _get_session_characters(db, db_session)
    config = get_effective_character_llm_config(current_user, sage_character)

    # Check if API key is configured (local models don't need one)
    from backend.services.llm.providers import provider_needs_api_key
    if provider_needs_api_key(config.provider) and not config.api_key:
        return ChatResponse(
            type="error",
            reply="⚠️ 请先在「系统设置」中配置 API Key，才能使用 AI 对话功能。\n\n点击右上角设置图标 → 填写对应 Provider 的 API Key → 保存设置",
            choices=None, emotion=None, relationship_stage=None,
            relationship=None, relationship_events=None,
            expression_hint="default", memory_extracted_count=0,
            narrative_events=None, new_achievements=None,
        )

    # Process message through LearningEngine
    # Note: LearningEngine handles session updates, we handle ChatMessage storage
    result = await learning_engine.process_message(
        session_id=db_session.id,
        user_message=chat_request.message,
        user_api_key=config.api_key,
        provider=config.provider,
        db=db,
        temperature=config.temperature,
        max_tokens=config.max_tokens,
        model=config.model,
        base_url=config.base_url,
    )

    # Save user message to database
    user_message = ChatMessage(
        session_id=db_session.id,
        sender_type="user",
        sender_id=current_user.id,
        content=chat_request.message,
        emotion_analysis=result.get("emotion"),
        used_memory_ids=result.get("used_memory_ids")
    )
    db.add(user_message)

    # Save teacher response to database
    teacher_message = ChatMessage(
        session_id=db_session.id,
        sender_type="teacher",
        content=result.get("reply", "")
    )
    db.add(teacher_message)
    db.commit()

    emotion_type = result.get("emotion", {}).get("emotion_type", "neutral") if result.get("emotion") else "neutral"
    expression = EXPRESSION_MAP.get(emotion_type, "default")

    return ChatResponse(
        type=result.get("type", "text"),
        reply=result.get("reply", ""),
        choices=result.get("choices"),
        emotion=result.get("emotion"),
        relationship_stage=result.get("relationship_stage"),
        relationship=result.get("relationship"),
        relationship_events=result.get("relationship_events"),
        expression_hint=expression,
        memory_extracted_count=result.get("memory_extracted_count", 0),
        narrative_events=result.get("narrative_events"),
        new_achievements=result.get("new_achievements"),
    )



# End learning session
@router.post("/sessions/{session_id}/end")
async def end_session(
    session_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    session = db.query(SessionModel).filter(
        SessionModel.id == session_id,
        SessionModel.user_id == current_user.id
    ).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    session.ended_at = datetime.now(UTC)

    # Update LearnerProfile session_count
    if session.learner_profile_id:
        from backend.models.models import LearnerProfile
        learner_profile = db.query(LearnerProfile).filter(
            LearnerProfile.id == session.learner_profile_id
        ).first()
        if learner_profile:
            profile = learner_profile.profile or {}
            profile["session_count"] = profile.get("session_count", 0) + 1
            learner_profile.profile = profile

    # Update UserProfile (incremental update)
    from backend.services.user_profile import update_user_profile_after_session_end
    update_user_profile_after_session_end(db, current_user.id, session.world_id)

    db.commit()

    return {"message": "Session ended"}


# Get chat history
@router.get("/sessions/{session_id}/history")
async def get_history(
    session_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    session = db.query(SessionModel).filter(
        SessionModel.id == session_id,
        SessionModel.user_id == current_user.id,
    ).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    messages = db.query(ChatMessage).filter(
        ChatMessage.session_id == session_id
    ).order_by(ChatMessage.timestamp).all()

    return [
        {
            "id": m.id,
            "sender_type": m.sender_type,
            "content": m.content,
            "timestamp": m.timestamp
        }
        for m in messages
    ]


# List user's sessions
@router.get("/sessions")
async def list_sessions(
    course_id: int | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    query = db.query(SessionModel).filter(
        SessionModel.user_id == current_user.id
    )
    if course_id:
        query = query.filter(SessionModel.course_id == course_id)

    sessions = query.order_by(SessionModel.started_at.desc()).all()
    return [
        {
            "id": s.id,
            "started_at": s.started_at,
            "ended_at": s.ended_at,
            "relationship_stage": s.relationship_stage,
            "course_name": s.course.name if s.course else None,
        }
        for s in sessions
    ]


# Get emotion trajectory for a session
@router.get("/sessions/{session_id}/emotion_trajectory")
async def get_emotion_trajectory(
    session_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Return emotion data for all user messages in a session."""
    session = db.query(SessionModel).filter(
        SessionModel.id == session_id,
        SessionModel.user_id == current_user.id
    ).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    messages = db.query(ChatMessage).filter(
        ChatMessage.session_id == session_id,
        ChatMessage.sender_type == "user",
        ChatMessage.emotion_analysis != None
    ).order_by(ChatMessage.timestamp).all()

    return [
        {
            "index": i + 1,
            "timestamp": m.timestamp,
            "emotion_type": m.emotion_analysis.get("emotion_type", "neutral"),
            "valence": m.emotion_analysis.get("valence", 0.5),
            "arousal": m.emotion_analysis.get("arousal", 0.5),
            "confidence": m.emotion_analysis.get("confidence", 0.0),
        }
        for i, m in enumerate(messages)
    ]


# ============================================
# User Profile - 用户全局画像
# ============================================

class RefreshUserProfileRequest(BaseModel):
    """手动刷新用户画像请求"""
    force: bool = Field(default=False, description="是否强制刷新（忽略缓存）")


@router.get("/user/profile", tags=["user"])
def get_user_profile(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    获取用户全局画像（跨世界特征聚合）

    返回数据包括：
    - metacognition_trend: 元认知趋势（MSKT四维度）
    - preference_stability: 偏好稳定性
    - learning_stats: 学习统计

    这是懒计算模式：数据超过24小时会自动重新计算
    """
    from backend.services.user_profile import get_user_profile as compute_user_profile

    profile = compute_user_profile(db, user.id)

    # 直接返回 profile，不包装 { success, data }
    return profile


@router.post("/user/profile/refresh", tags=["user"])
def refresh_user_profile(
    request: RefreshUserProfileRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    手动刷新用户画像

    如果 force=True，忽略缓存强制重新计算
    """
    from backend.services.user_profile import get_or_create_user_profile

    user_profile = get_or_create_user_profile(db, user.id)

    if request.force:
        # 清除缓存时间戳以触发重新计算
        user_profile.computed_at = None
        db.commit()

    # 使用与 GET 相同的 get_user_profile 来确保重新计算
    from backend.services.user_profile import get_user_profile as compute_user_profile
    profile = compute_user_profile(db, user.id)

    # 与 GET /user/profile 保持一致：直接返回 profile
    return profile

