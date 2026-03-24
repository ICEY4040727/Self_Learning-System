from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime, ForeignKey, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from backend.db.database import Base


class Tenant(Base):
    __tablename__ = "tenants"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    created_at = Column(DateTime, server_default=func.now())

    users = relationship("User", back_populates="tenant")
    characters = relationship("Character", back_populates="tenant")
    subjects = relationship("Subject", back_populates="tenant")
    teacher_personas = relationship("TeacherPersona", back_populates="tenant")


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id"))
    username = Column(String(50), unique=True, index=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    role = Column(String(20), default="student")
    encrypted_api_key = Column(String(255), nullable=True)
    default_provider = Column(String(50), nullable=True)
    created_at = Column(DateTime, server_default=func.now())

    tenant = relationship("Tenant", back_populates="users")
    characters = relationship("Character", back_populates="user")
    learner_profiles = relationship("LearnerProfile", back_populates="user")
    learning_diaries = relationship("LearningDiary", back_populates="user")
    progress_trackings = relationship("ProgressTracking", back_populates="user")
    sessions = relationship("Session", back_populates="user")
    saves = relationship("Save", back_populates="user")


class Character(Base):
    __tablename__ = "characters"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id"))
    user_id = Column(Integer, ForeignKey("users.id"))
    name = Column(String(100), nullable=False)
    avatar = Column(String(255), nullable=True)
    personality = Column(Text, nullable=True)
    background = Column(Text, nullable=True)
    speech_style = Column(Text, nullable=True)
    created_at = Column(DateTime, server_default=func.now())

    tenant = relationship("Tenant", back_populates="characters")
    user = relationship("User", back_populates="characters")
    subjects = relationship("Subject", back_populates="character")
    teacher_personas = relationship("TeacherPersona", back_populates="character")


class TeacherPersona(Base):
    __tablename__ = "teacher_personas"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id"))
    character_id = Column(Integer, ForeignKey("characters.id"))
    name = Column(String(100), nullable=False)
    version = Column(String(20), default="1.0")
    traits = Column(JSON, nullable=True)
    system_prompt_template = Column(Text, nullable=True)
    is_active = Column(Boolean, default=False)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    tenant = relationship("Tenant", back_populates="teacher_personas")
    character = relationship("Character", back_populates="teacher_personas")
    sessions = relationship("Session", back_populates="teacher_persona")


class LearnerProfile(Base):
    __tablename__ = "learner_profiles"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id"))
    user_id = Column(Integer, ForeignKey("users.id"))
    subject_id = Column(Integer, ForeignKey("subjects.id"), nullable=True)
    learning_style = Column(JSON, nullable=True)
    cognitive_traits = Column(JSON, nullable=True)
    emotional_traits = Column(JSON, nullable=True)
    knowledge_graph = Column(JSON, nullable=True)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    user = relationship("User", back_populates="learner_profiles")
    subject = relationship("Subject", back_populates="learner_profiles")
    sessions = relationship("Session", back_populates="learner_profile")


class Subject(Base):
    __tablename__ = "subjects"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id"))
    character_id = Column(Integer, ForeignKey("characters.id"))
    name = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)
    target_level = Column(String(50), nullable=True)
    created_at = Column(DateTime, server_default=func.now())

    tenant = relationship("Tenant", back_populates="subjects")
    character = relationship("Character", back_populates="subjects")
    learner_profiles = relationship("LearnerProfile", back_populates="subject")
    lesson_plans = relationship("LessonPlan", back_populates="subject")
    learning_diaries = relationship("LearningDiary", back_populates="subject")
    progress_trackings = relationship("ProgressTracking", back_populates="subject")
    sessions = relationship("Session", back_populates="subject")


class LessonPlan(Base):
    __tablename__ = "lesson_plans"

    id = Column(Integer, primary_key=True, index=True)
    subject_id = Column(Integer, ForeignKey("subjects.id"))
    content = Column(Text, nullable=False)
    created_at = Column(DateTime, server_default=func.now())

    subject = relationship("Subject", back_populates="lesson_plans")


class LearningDiary(Base):
    __tablename__ = "learning_diaries"

    id = Column(Integer, primary_key=True, index=True)
    subject_id = Column(Integer, ForeignKey("subjects.id"))
    user_id = Column(Integer, ForeignKey("users.id"))
    date = Column(DateTime, nullable=False)
    content = Column(Text, nullable=False)
    reflection = Column(Text, nullable=True)

    subject = relationship("Subject", back_populates="learning_diaries")
    user = relationship("User", back_populates="learning_diaries")


class ProgressTracking(Base):
    __tablename__ = "progress_trackings"

    id = Column(Integer, primary_key=True, index=True)
    subject_id = Column(Integer, ForeignKey("subjects.id"))
    user_id = Column(Integer, ForeignKey("users.id"))
    topic = Column(String(100), nullable=False)
    mastery_level = Column(Integer, default=0)
    last_review = Column(DateTime, nullable=True)
    next_review = Column(DateTime, nullable=True)

    subject = relationship("Subject", back_populates="progress_trackings")
    user = relationship("User", back_populates="progress_trackings")


class Session(Base):
    __tablename__ = "sessions"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id"))
    subject_id = Column(Integer, ForeignKey("subjects.id"))
    user_id = Column(Integer, ForeignKey("users.id"))
    started_at = Column(DateTime, server_default=func.now())
    ended_at = Column(DateTime, nullable=True)
    system_prompt = Column(Text, nullable=True)
    relationship_stage = Column(String(20), default="stranger")
    teacher_persona_id = Column(Integer, ForeignKey("teacher_personas.id"), nullable=True)
    learner_profile_id = Column(Integer, ForeignKey("learner_profiles.id"), nullable=True)

    tenant = relationship("Tenant")
    subject = relationship("Subject", back_populates="sessions")
    user = relationship("User", back_populates="sessions")
    teacher_persona = relationship("TeacherPersona", back_populates="sessions")
    learner_profile = relationship("LearnerProfile", back_populates="sessions")
    chat_messages = relationship("ChatMessage", back_populates="session")
    relationship_stage_records = relationship("RelationshipStageRecord", back_populates="session")


class ChatMessage(Base):
    __tablename__ = "chat_messages"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(Integer, ForeignKey("sessions.id"))
    sender_type = Column(String(20), nullable=False)  # user, teacher
    sender_id = Column(Integer, nullable=True)
    content = Column(Text, nullable=False)
    timestamp = Column(DateTime, server_default=func.now())
    emotion_analysis = Column(JSON, nullable=True)
    used_memory_ids = Column(JSON, nullable=True)

    session = relationship("Session", back_populates="chat_messages")


class RelationshipStageRecord(Base):
    __tablename__ = "relationship_stages"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(Integer, ForeignKey("sessions.id"))
    stage = Column(String(20), nullable=False)
    reason = Column(Text, nullable=True)
    updated_at = Column(DateTime, server_default=func.now())

    session = relationship("Session", back_populates="relationship_stage_records")


class Save(Base):
    __tablename__ = "saves"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    subject_id = Column(Integer, ForeignKey("subjects.id"))
    session_id = Column(Integer, ForeignKey("sessions.id"), nullable=True)
    save_name = Column(String(100), nullable=False)
    file_path = Column(String(255), nullable=False)
    memory_ids = Column(JSON, nullable=True)
    created_at = Column(DateTime, server_default=func.now())

    user = relationship("User", back_populates="saves")
    subject = relationship("Subject")
    session = relationship("Session")