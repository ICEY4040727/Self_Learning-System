from datetime import UTC, datetime

from sqlalchemy import (
    JSON,
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import attributes
from sqlalchemy.orm import relationship as orm_relationship

from backend.db.database import Base


def _utcnow():
    return datetime.now(UTC)


def _default_relationship():
    return {
        "dimensions": {
            "trust": 0.0,
            "familiarity": 0.0,
            "respect": 0.0,
            "comfort": 0.0,
        },
        "stage": "stranger",
        "history": [],
    }


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, index=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    role = Column(String(20), default="student")
    encrypted_api_key = Column(String(255), nullable=True)
    default_provider = Column(String(50), nullable=True)
    created_at = Column(DateTime, default=_utcnow)

    worlds = orm_relationship("World", back_populates="user", cascade="all, delete-orphan")
    characters = orm_relationship("Character", back_populates="user", cascade="all, delete-orphan")
    learner_profiles = orm_relationship("LearnerProfile", back_populates="user", cascade="all, delete-orphan")
    learning_diaries = orm_relationship("LearningDiary", back_populates="user", cascade="all, delete-orphan")
    progress_trackings = orm_relationship("ProgressTracking", back_populates="user", cascade="all, delete-orphan")
    sessions = orm_relationship("Session", back_populates="user", cascade="all, delete-orphan")
    checkpoints = orm_relationship("Checkpoint", back_populates="user", cascade="all, delete-orphan")
    user_profile = orm_relationship("UserProfile", back_populates="user", uselist=False, cascade="all, delete-orphan")


class UserProfile(Base):
    """用户全局画像 - 跨世界特征聚合（仅用于展示，不注入提示词）"""
    __tablename__ = "user_profiles"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True, nullable=False)
    profile = Column(JSON, nullable=False, default=dict)  # 跨世界汇总数据
    computed_at = Column(DateTime, default=_utcnow)
    created_at = Column(DateTime, default=_utcnow)
    updated_at = Column(DateTime, default=_utcnow, onupdate=_utcnow)

    user = orm_relationship("User", back_populates="user_profile")


class World(Base):
    __tablename__ = "worlds"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    name = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)
    scenes = Column(JSON, nullable=False, default=dict)
    created_at = Column(DateTime, default=_utcnow)

    user = orm_relationship("User", back_populates="worlds")
    world_characters = orm_relationship("WorldCharacter", back_populates="world", cascade="all, delete-orphan")
    courses = orm_relationship("Course", back_populates="world", cascade="all, delete-orphan")
    sessions = orm_relationship("Session", back_populates="world", cascade="all, delete-orphan")
    checkpoints = orm_relationship("Checkpoint", back_populates="world", cascade="all, delete-orphan")
    learner_profiles = orm_relationship("LearnerProfile", back_populates="world", cascade="all, delete-orphan")
    knowledge = orm_relationship("Knowledge", back_populates="world", uselist=False, cascade="all, delete-orphan")
    fsrs_states = orm_relationship("FSRSState", back_populates="world", cascade="all, delete-orphan")


# 角色类型说明 (Character.type):
#   - "sage": 导师角色 (AI教师)
#   - "traveler": 旅人角色 (玩家在游戏世界中的化身)
class Character(Base):
    __tablename__ = "characters"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    name = Column(String(100), nullable=False)
    # type: "sage" | "traveler" - 区分导师角色和学习者角色
    type = Column(String(20), nullable=False, default="sage")
    avatar = Column(String(255), nullable=True)
    personality = Column(Text, nullable=True)
    background = Column(Text, nullable=True)
    speech_style = Column(Text, nullable=True)
    sprites = Column(JSON, nullable=True)
    title = Column(String(100), nullable=True)  # 知者名片头衔
    tags = Column(JSON, nullable=True, default=list)  # 角色标签列表
    experience_points = Column(Integer, nullable=False, default=0)  # 经验值
    level = Column(Integer, nullable=False, default=1)  # 等级
    created_at = Column(DateTime, default=_utcnow)

    user = orm_relationship("User", back_populates="characters")
    teacher_personas = orm_relationship("TeacherPersona", back_populates="character", cascade="all, delete-orphan")
    world_links = orm_relationship("WorldCharacter", back_populates="character", cascade="all, delete-orphan")


class WorldCharacter(Base):
    __tablename__ = "world_characters"
    __table_args__ = (UniqueConstraint("world_id", "character_id", name="uq_world_character"),)

    id = Column(Integer, primary_key=True, index=True)
    world_id = Column(Integer, ForeignKey("worlds.id", ondelete="CASCADE"), nullable=False)
    character_id = Column(Integer, ForeignKey("characters.id", ondelete="CASCADE"), nullable=False)
    role = Column(String(20), nullable=False)
    is_primary = Column(Boolean, default=False)

    world = orm_relationship("World", back_populates="world_characters")
    character = orm_relationship("Character", back_populates="world_links")


class Knowledge(Base):
    __tablename__ = "knowledge"

    world_id = Column(Integer, ForeignKey("worlds.id", ondelete="CASCADE"), primary_key=True)
    graph = Column(JSON, nullable=False, default=dict)

    world = orm_relationship("World", back_populates="knowledge")


class TeacherPersona(Base):
    __tablename__ = "teacher_personas"

    id = Column(Integer, primary_key=True, index=True)
    character_id = Column(Integer, ForeignKey("characters.id"), nullable=False)
    name = Column(String(100), nullable=False)
    version = Column(String(20), default="1.0")
    traits = Column(JSON, nullable=True)
    system_prompt_template = Column(Text, nullable=True)
    is_active = Column(Boolean, default=False)
    created_at = Column(DateTime, default=_utcnow)
    updated_at = Column(DateTime, default=_utcnow, onupdate=_utcnow)

    character = orm_relationship("Character", back_populates="teacher_personas")
    sessions = orm_relationship("Session", back_populates="teacher_persona")


# 学习者档案 (LearnerProfile):
# 存储用户在特定世界中的学习状态、偏好、元认知等信息
# 注意：这是"学习追踪层"，与游戏角色层(traveler)是不同概念
class LearnerProfile(Base):
    __tablename__ = "learner_profiles"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    world_id = Column(Integer, ForeignKey("worlds.id", ondelete="CASCADE"), nullable=False)
    profile = Column(JSON, nullable=False, default=dict)
    created_at = Column(DateTime, default=_utcnow)
    updated_at = Column(DateTime, default=_utcnow, onupdate=_utcnow)

    user = orm_relationship("User", back_populates="learner_profiles")
    world = orm_relationship("World", back_populates="learner_profiles")
    sessions = orm_relationship("Session", back_populates="learner_profile")


class Course(Base):
    __tablename__ = "courses"

    id = Column(Integer, primary_key=True, index=True)
    world_id = Column(Integer, ForeignKey("worlds.id", ondelete="CASCADE"), nullable=False)
    name = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)
    target_level = Column(String(50), nullable=True)
    # meta JSON: 存储表单扩展字段 (current_level, motivation, pace, weekly_minutes, sage_ids 等)
    # 见文档: docs/v1.0.0前后端联调修复/世界_课程_角色_表单设计.md 附录 A
    meta = Column(JSON, nullable=True, default=dict)
    created_at = Column(DateTime, default=_utcnow)

    world = orm_relationship("World", back_populates="courses")
    lesson_plans = orm_relationship("LessonPlan", back_populates="course", cascade="all, delete-orphan")
    learning_diaries = orm_relationship("LearningDiary", back_populates="course", cascade="all, delete-orphan")
    progress_trackings = orm_relationship("ProgressTracking", back_populates="course", cascade="all, delete-orphan")
    sessions = orm_relationship("Session", back_populates="course", cascade="all, delete-orphan")


class LessonPlan(Base):
    __tablename__ = "lesson_plans"

    id = Column(Integer, primary_key=True, index=True)
    course_id = Column(Integer, ForeignKey("courses.id"), nullable=False)
    content = Column(Text, nullable=False)
    created_at = Column(DateTime, default=_utcnow)

    course = orm_relationship("Course", back_populates="lesson_plans")


class LearningDiary(Base):
    __tablename__ = "learning_diaries"

    id = Column(Integer, primary_key=True, index=True)
    course_id = Column(Integer, ForeignKey("courses.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    date = Column(DateTime, nullable=False)
    content = Column(Text, nullable=False)
    reflection = Column(Text, nullable=True)

    course = orm_relationship("Course", back_populates="learning_diaries")
    user = orm_relationship("User", back_populates="learning_diaries")


class ProgressTracking(Base):
    __tablename__ = "progress_trackings"

    id = Column(Integer, primary_key=True, index=True)
    course_id = Column(Integer, ForeignKey("courses.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    topic = Column(String(100), nullable=False)
    mastery_level = Column(Integer, default=0)
    last_review = Column(DateTime, nullable=True)
    next_review = Column(DateTime, nullable=True)

    course = orm_relationship("Course", back_populates="progress_trackings")
    user = orm_relationship("User", back_populates="progress_trackings")


class FSRSState(Base):
    __tablename__ = "fsrs_states"
    __table_args__ = (UniqueConstraint("world_id", "concept_id", name="uq_fsrs_world_concept"),)

    id = Column(Integer, primary_key=True, index=True)
    world_id = Column(Integer, ForeignKey("worlds.id", ondelete="CASCADE"), nullable=False)
    concept_id = Column(String(150), nullable=False)
    difficulty = Column(Float, nullable=True)
    stability = Column(Float, nullable=True)
    last_review = Column(DateTime, nullable=True)
    next_review = Column(DateTime, nullable=True)
    reps = Column(Integer, default=0)

    world = orm_relationship("World", back_populates="fsrs_states")


# 会话模型 (Session):
# 一个学习会话关联多个角色和档案:
#   - sage_character_id: 导师角色 (Character.type="sage") - AI教师角色
#   - traveler_character_id: 旅人角色 (Character.type="traveler") - 玩家游戏化身
#   - teacher_persona_id: 教师人格 - 导师的具体人格设定
#   - learner_profile_id: 学习者档案 - 记录用户学习状态
#
# 层级区分:
#   - traveler: 游戏角色层 (故事/游戏中玩家扮演的角色)
#   - learner_profile: 学习追踪层 (记录用户学习状态、偏好)
class Session(Base):
    __tablename__ = "sessions"

    id = Column(Integer, primary_key=True, index=True)
    course_id = Column(Integer, ForeignKey("courses.id", ondelete="CASCADE"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    world_id = Column(Integer, ForeignKey("worlds.id", ondelete="CASCADE"), nullable=False)
    # 角色关联 (游戏角色层)
    sage_character_id = Column(Integer, ForeignKey("characters.id"), nullable=True)
    traveler_character_id = Column(Integer, ForeignKey("characters.id"), nullable=True)
    started_at = Column(DateTime, default=_utcnow)
    ended_at = Column(DateTime, nullable=True)
    system_prompt = Column(Text, nullable=True)
    relationship = Column(JSON, nullable=False, default=_default_relationship)
    # Optional links: sessions may start without active persona/profile or branch parent.
    teacher_persona_id = Column(Integer, ForeignKey("teacher_personas.id"), nullable=True)
    learner_profile_id = Column(Integer, ForeignKey("learner_profiles.id"), nullable=True)
    parent_checkpoint_id = Column(Integer, ForeignKey("checkpoints.id"), nullable=True)
    branch_name = Column(String(120), nullable=True)

    course = orm_relationship("Course", back_populates="sessions")
    user = orm_relationship("User", back_populates="sessions")
    world = orm_relationship("World", back_populates="sessions")
    teacher_persona = orm_relationship("TeacherPersona", back_populates="sessions")
    learner_profile = orm_relationship("LearnerProfile", back_populates="sessions")
    chat_messages = orm_relationship("ChatMessage", back_populates="session", cascade="all, delete-orphan")
    relationship_stage_records = orm_relationship("RelationshipStageRecord", back_populates="session", cascade="all, delete-orphan")
    parent_checkpoint = orm_relationship("Checkpoint", foreign_keys=[parent_checkpoint_id], post_update=True)

    @property
    def relationship_stage(self):
        rel = self.relationship or {}
        return rel.get("stage", "stranger")

    @relationship_stage.setter
    def relationship_stage(self, stage: str):
        rel = dict(self.relationship or _default_relationship())
        rel["stage"] = stage or "stranger"
        self.relationship = rel
        attributes.flag_modified(self, "relationship")


class ChatMessage(Base):
    __tablename__ = "chat_messages"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(Integer, ForeignKey("sessions.id"), nullable=False)
    sender_type = Column(String(20), nullable=False)
    sender_id = Column(Integer, nullable=True)
    content = Column(Text, nullable=False)
    timestamp = Column(DateTime, default=_utcnow)
    emotion_analysis = Column(JSON, nullable=True)
    used_memory_ids = Column(JSON, nullable=True)

    session = orm_relationship("Session", back_populates="chat_messages")


class RelationshipStageRecord(Base):
    __tablename__ = "relationship_stages"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(Integer, ForeignKey("sessions.id"), nullable=False)
    stage = Column(String(20), nullable=False)
    reason = Column(Text, nullable=True)
    updated_at = Column(DateTime, default=_utcnow)

    session = orm_relationship("Session", back_populates="relationship_stage_records")


class Checkpoint(Base):
    __tablename__ = "checkpoints"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    world_id = Column(Integer, ForeignKey("worlds.id", ondelete="CASCADE"), nullable=False)
    session_id = Column(Integer, ForeignKey("sessions.id"), nullable=True)
    save_name = Column(String(100), nullable=False)
    message_index = Column(Integer, nullable=False, default=0)
    state = Column(JSON, nullable=False, default=dict)
    thumbnail_path = Column(String(255), nullable=True)
    created_at = Column(DateTime, default=_utcnow)

    user = orm_relationship("User", back_populates="checkpoints")
    world = orm_relationship("World", back_populates="checkpoints")
    session = orm_relationship("Session", foreign_keys=[session_id])

