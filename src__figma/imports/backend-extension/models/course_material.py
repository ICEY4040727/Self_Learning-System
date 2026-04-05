"""
models/course_material.py
──────────────────────────────────────────────────────────────
CourseMaterial — 课程教材资料上传记录

字段说明：
  filename          服务端存储文件名（含扩展名，去歧义后唯一）
  original_filename 用户上传时的原始文件名（保留用于展示）
  content_type      MIME 类型（前端上传约束的镜像）
  file_size         字节数（< 10 MB 硬限）
  text_content      提取后的纯文本（供 AI 服务消费）
  extraction_status pending | processing | ready | error
  error_message     提取失败时的错误描述
──────────────────────────────────────────────────────────────
"""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import (
    Column, DateTime, ForeignKey, Integer, String, Text, func
)
from sqlalchemy.orm import relationship

from backend.database import Base  # 复用现有 Base


ALLOWED_CONTENT_TYPES = {
    "text/plain",
    "text/markdown",
    "application/pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",  # .docx
    "application/msword",  # .doc (limited support)
}

MAX_MATERIAL_SIZE_BYTES = 10 * 1024 * 1024  # 10 MB

ExtractionStatus = str  # 'pending' | 'processing' | 'ready' | 'error'


class CourseMaterial(Base):
    __tablename__ = "course_materials"

    id                = Column(Integer, primary_key=True, index=True)
    course_id         = Column(Integer, ForeignKey("courses.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id           = Column(Integer, ForeignKey("users.id",   ondelete="CASCADE"), nullable=False, index=True)

    # File identity
    filename          = Column(String(512), nullable=False)           # server-side unique name
    original_filename = Column(String(512), nullable=False)           # display name
    content_type      = Column(String(128), nullable=False)
    file_size         = Column(Integer,     nullable=False)           # bytes

    # Extracted content
    text_content      = Column(Text, nullable=True)                   # populated after extraction
    extraction_status = Column(String(20), default="pending", nullable=False)
    error_message     = Column(Text, nullable=True)

    created_at        = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at        = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    course = relationship("Course", back_populates="materials")
    user   = relationship("User")

    def __repr__(self) -> str:
        return f"<CourseMaterial id={self.id} course={self.course_id} file={self.original_filename!r}>"
