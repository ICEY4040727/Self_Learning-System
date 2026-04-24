"""教材上传 + AI 课程生成 API

Phase 3 Step 2: 学生上传教材 → AI 分析 → 生成课程结构
"""

import json
import logging
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, UploadFile
from pydantic import BaseModel
from sqlalchemy.orm import Session

from backend.api.routes.auth import get_current_user
from backend.db.database import get_db
from backend.models.models import Course, Textbook, User, World

logger = logging.getLogger(__name__)

router = APIRouter()

# ── 配置 ──────────────────────────────────────────────────────────────

ALLOWED_EXTENSIONS = {".pdf", ".txt", ".md", ".markdown", ".epub"}
MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB
TEXT_PREVIEW_LENGTH = 500


# ── Pydantic Schemas ──────────────────────────────────────────────────


class TextbookResponse(BaseModel):
    id: int
    course_id: int
    filename: str
    file_size: int | None = None
    content_type: str | None = None
    page_count: int | None = None
    status: str = "uploaded"
    error_message: str | None = None
    created_at: str | None = None

    class Config:
        from_attributes = True


class CourseGenerateRequest(BaseModel):
    """AI 课程生成请求"""
    course_id: int
    # 可选的自定义指令
    custom_instructions: str | None = None
    # 目标学习天数
    target_days: int | None = None


class GeneratedLessonResponse(BaseModel):
    """生成的单节课"""
    title: str
    description: str
    order: int
    concepts: list[str]
    prerequisites: list[str] = []


class CourseGenerateResponse(BaseModel):
    """课程生成结果"""
    course_id: int
    overview: str
    lessons: list[GeneratedLessonResponse]
    concept_map: dict | None = None
    textbook_count: int = 0
    total_chars: int = 0


# ── 工具函数 ──────────────────────────────────────────────────────────


def _get_course_with_auth(course_id: int, db: Session, current_user: User) -> Course:
    """验证课程存在且用户有权限"""
    course = db.query(Course).join(World, Course.world_id == World.id).filter(
        Course.id == course_id,
        World.user_id == current_user.id,
    ).first()
    if not course:
        raise HTTPException(status_code=404, detail="课程不存在")
    return course


def _extract_text_from_bytes(content: bytes, filename: str) -> str:
    """从上传文件中提取纯文本

    支持: .txt, .md, .pdf (基础提取)
    """
    ext = Path(filename).suffix.lower()

    if ext in {".txt", ".md", ".markdown"}:
        # 尝试多种编码
        for encoding in ("utf-8", "gbk", "gb2312", "latin-1"):
            try:
                return content.decode(encoding)
            except (UnicodeDecodeError, LookupError):
                continue
        return content.decode("utf-8", errors="replace")

    if ext == ".pdf":
        try:
            import fitz  # PyMuPDF
            import io
            doc = fitz.open(stream=io.BytesIO(content), filetype="pdf")
            pages = []
            for page in doc:
                pages.append(page.get_text())
            doc.close()
            return "\n\n".join(pages)
        except ImportError:
            # PyMuPDF 未安装，回退到提示
            return "[PDF 文件需要安装 PyMuPDF 库才能提取文本]"
        except Exception as e:
            return f"[PDF 文本提取失败: {e}]"

    if ext == ".epub":
        try:
            import zipfile
            import io
            with zipfile.ZipFile(io.BytesIO(content)) as zf:
                texts = []
                for name in zf.namelist():
                    if name.endswith((".html", ".xhtml", ".htm")):
                        raw = zf.read(name).decode("utf-8", errors="replace")
                        # 简单去除 HTML 标签
                        import re
                        clean = re.sub(r"<[^>]+>", "", raw)
                        clean = re.sub(r"\s+", " ", clean).strip()
                        if clean:
                            texts.append(clean)
                return "\n\n".join(texts)
        except Exception as e:
            return f"[EPUB 文本提取失败: {e}]"

    return f"[不支持的文件类型: {ext}]"


# ── API 端点 ──────────────────────────────────────────────────────────


@router.post("/courses/{course_id}/textbooks", response_model=TextbookResponse)
async def upload_textbook(
    course_id: int,
    file: UploadFile,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """上传教材文件到指定课程

    支持 PDF、TXT、MD、EPUB 格式，最大 50MB。
    上传后自动提取文本内容。
    """
    course = _get_course_with_auth(course_id, db, current_user)

    # 验证文件类型
    filename = file.filename or "unknown.txt"
    ext = Path(filename).suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=422,
            detail=f"不支持的文件类型 '{ext}'，允许: {', '.join(sorted(ALLOWED_EXTENSIONS))}",
        )

    # 读取文件内容
    content = await file.read()
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(status_code=413, detail="文件超过 50MB 限制")

    # 存储文件到 static 目录
    static_dir = Path(__file__).resolve().parents[2] / "static" / "textbooks" / str(course_id)
    static_dir.mkdir(parents=True, exist_ok=True)

    # 生成唯一文件名避免冲突
    import time
    safe_name = f"{int(time.time())}_{filename}"
    file_path = static_dir / safe_name
    file_path.write_bytes(content)

    # 提取文本
    extracted_text = _extract_text_from_bytes(content, filename)
    page_count = None
    if ext == ".pdf":
        try:
            import fitz
            import io
            doc = fitz.open(stream=io.BytesIO(content), filetype="pdf")
            page_count = len(doc)
            doc.close()
        except Exception:
            pass

    # 保存到数据库
    textbook = Textbook(
        course_id=course_id,
        user_id=current_user.id,
        filename=filename,
        file_path=str(file_path),
        file_size=len(content),
        content_type=file.content_type,
        extracted_text=extracted_text,
        page_count=page_count,
        status="extracted",
    )
    db.add(textbook)
    db.commit()
    db.refresh(textbook)

    logger.info("教材上传成功: course_id=%d, textbook_id=%d, filename=%s, size=%d",
                course_id, textbook.id, filename, len(content))

    return textbook


@router.get("/courses/{course_id}/textbooks", response_model=list[TextbookResponse])
def list_textbooks(
    course_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """获取课程的所有教材"""
    _get_course_with_auth(course_id, db, current_user)

    textbooks = db.query(Textbook).filter(
        Textbook.course_id == course_id,
        Textbook.user_id == current_user.id,
    ).order_by(Textbook.created_at.desc()).all()

    return textbooks


@router.delete("/courses/{course_id}/textbooks/{textbook_id}")
def delete_textbook(
    course_id: int,
    textbook_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """删除教材"""
    _get_course_with_auth(course_id, db, current_user)

    textbook = db.query(Textbook).filter(
        Textbook.id == textbook_id,
        Textbook.course_id == course_id,
        Textbook.user_id == current_user.id,
    ).first()
    if not textbook:
        raise HTTPException(status_code=404, detail="教材不存在")

    # 删除文件
    try:
        file_path = Path(textbook.file_path)
        if file_path.exists():
            file_path.unlink()
    except Exception as e:
        logger.warning("教材文件删除失败: %s", e)

    db.delete(textbook)
    db.commit()
    return {"message": "教材已删除"}


@router.post("/courses/{course_id}/generate", response_model=CourseGenerateResponse)
async def generate_course_from_textbooks(
    course_id: int,
    req: CourseGenerateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """基于上传的教材 AI 生成课程结构

    从教材中提取的知识点自动生成:
    - 课程概览
    - 章节列表 (lessons)
    - 概念图 (concept_map)
    """
    course = _get_course_with_auth(course_id, db, current_user)

    # 获取课程关联的所有已提取文本的教材
    textbooks = db.query(Textbook).filter(
        Textbook.course_id == course_id,
        Textbook.user_id == current_user.id,
        Textbook.status == "extracted",
        Textbook.extracted_text.isnot(None),
    ).all()

    if not textbooks:
        raise HTTPException(
            status_code=400,
            detail="没有可用的教材文本，请先上传教材并等待文本提取完成",
        )

    # 合并所有教材文本
    all_text = "\n\n---\n\n".join(t.extracted_text for t in textbooks if t.extracted_text)
    total_chars = len(all_text)

    # 截断过长文本（LLM 上下文限制）
    MAX_CHARS = 80000
    if total_chars > MAX_CHARS:
        # 取前 MAX_CHARS 字符，保留开头和结尾
        half = MAX_CHARS // 2
        all_text = all_text[:half] + "\n\n[... 中间内容已省略 ...]\n\n" + all_text[-half:]

    # 调用 AI 生成课程
    from backend.services.course_generator import CourseGenerator
    generator = CourseGenerator()

    # 获取用户的 API key
    user_api_key = None
    if current_user.encrypted_api_key:
        from backend.core.security import decrypt_api_key
        try:
            user_api_key = decrypt_api_key(current_user.encrypted_api_key)
        except Exception:
            pass

    try:
        result = await generator.generate(
            text=all_text,
            course_name=course.name,
            course_description=course.description,
            target_level=course.target_level,
            custom_instructions=req.custom_instructions,
            target_days=req.target_days,
            user_api_key=user_api_key,
            default_provider=current_user.default_provider,
        )
    except Exception as e:
        logger.error("课程生成失败: %s", e)
        raise HTTPException(status_code=500, detail=f"课程生成失败: {e}")

    # 更新教材状态
    for t in textbooks:
        t.status = "processed"
    db.commit()

    # 将生成结果存入课程 meta
    if not course.meta:
        course.meta = {}
    course.meta["generated_overview"] = result.get("overview", "")
    course.meta["generated_lessons"] = [l.model_dump() for l in result.get("lessons", [])]
    course.meta["concept_map"] = result.get("concept_map")
    from sqlalchemy.orm.attributes import flag_modified
    flag_modified(course, "meta")
    db.commit()

    return CourseGenerateResponse(
        course_id=course_id,
        overview=result.get("overview", ""),
        lessons=result.get("lessons", []),
        concept_map=result.get("concept_map"),
        textbook_count=len(textbooks),
        total_chars=total_chars,
    )


# ── 课程教学进度 API (Phase 3 Step 3) ─────────────────────────────────


class LessonProgressResponse(BaseModel):
    """课程进度响应"""
    total_lessons: int = 0
    current_index: int = 0
    completed_lessons: int = 0
    progress_pct: float = 0.0
    current_lesson: dict | None = None
    lessons: list[dict] = []


class SetLessonRequest(BaseModel):
    """手动设置当前章节请求"""
    lesson_index: int


@router.get("/courses/{course_id}/progress", response_model=LessonProgressResponse)
def get_course_progress(
    course_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """获取课程教学进度"""
    course = _get_course_with_auth(course_id, db, current_user)

    from backend.services.teaching_planner import teaching_planner
    progress = teaching_planner.get_progress(db, course)
    return progress


@router.post("/courses/{course_id}/advance", response_model=LessonProgressResponse)
def advance_lesson(
    course_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """推进到下一课"""
    course = _get_course_with_auth(course_id, db, current_user)

    from backend.services.teaching_planner import teaching_planner
    result = teaching_planner.advance_lesson(db, course)
    db.commit()

    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    return result


class CourseMasteryResponse(BaseModel):
    """课程掌握度概览"""
    overall_mastery: float = 0.0
    concepts: dict[str, int] = {}
    weak_concepts: list[str] = []
    mastered_count: int = 0
    total_tracked: int = 0


@router.get("/courses/{course_id}/mastery", response_model=CourseMasteryResponse)
def get_course_mastery(
    course_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """获取课程概念掌握度概览"""
    _get_course_with_auth(course_id, db, current_user)

    from backend.services.mastery_tracker import mastery_tracker
    return mastery_tracker.get_course_mastery(db, course_id)


@router.put("/courses/{course_id}/lesson", response_model=LessonProgressResponse)
def set_current_lesson(
    course_id: int,
    req: SetLessonRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """手动设置当前教学章节"""
    course = _get_course_with_auth(course_id, db, current_user)

    from backend.services.teaching_planner import teaching_planner
    result = teaching_planner.set_lesson(db, course, req.lesson_index)
    db.commit()

    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    return result
