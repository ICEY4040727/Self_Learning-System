"""教材上传 + AI 课程生成 API

Phase 3 Step 2: 学生上传教材 → AI 分析 → 生成课程结构
"""

import json
import logging
import secrets
from datetime import datetime
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, UploadFile
from fastapi.responses import FileResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

from backend.api.routes.auth import get_current_user
from backend.core.config import get_settings
from backend.db.database import get_db
from backend.models.models import Course, Textbook, User, World

logger = logging.getLogger(__name__)

router = APIRouter()

# ── 配置 ──────────────────────────────────────────────────────────────

ALLOWED_EXTENSIONS = {".pdf", ".txt", ".md", ".markdown", ".epub"}
MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB
TEXT_PREVIEW_LENGTH = 500
MAX_GENERATION_CHARS = 80000  # LLM context budget for course generation

# [TR-X12] Chapter-boundary detection for truncation. Patterns ordered by
# preference; the first match in the prefix wins. Multiline so ^ matches
# line start.
import re as _re
_CHAPTER_PATTERNS = [
    _re.compile(r"^#{1,3}\s+\S", _re.MULTILINE),                          # markdown # / ## / ###
    _re.compile(r"^第\s*[一二三四五六七八九十百千零〇\d]+\s*[章节回]\b", _re.MULTILINE),  # 第N章/节/回
    _re.compile(r"^Chapter\s+\d+\b", _re.MULTILINE | _re.IGNORECASE),     # Chapter 1
    _re.compile(r"^Section\s+\d+\b", _re.MULTILINE | _re.IGNORECASE),     # Section 1
]


def _truncate_at_chapter_boundary(text: str, limit: int) -> str:
    """[TR-X12] If ``text`` exceeds ``limit`` chars, truncate at the last
    chapter heading found within the first ``limit`` chars — but only
    when at least **two** chapter headings exist there.

    Why two: cutting AT a heading drops everything starting from that
    heading. With just one heading found in head, that heading marks the
    only chapter we have; cutting at it would discard the chapter
    entirely, leaving only the preamble. Falling back to a hard cut at
    least preserves the partial chapter.

    With ≥ 2 headings, we cut at the last one — keeping all complete
    chapters before it, dropping the partial chapter that runs past the
    limit. This is the intended behaviour: LLM sees the textbook's
    natural prefix structure rather than a sliced-up middle.
    """
    if len(text) <= limit:
        return text

    head = text[:limit]
    positions: list[int] = []
    for pattern in _CHAPTER_PATTERNS:
        positions.extend(m.start() for m in pattern.finditer(head))
    positions.sort()

    if len(positions) >= 2:
        return text[:positions[-1]].rstrip()
    return head


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
    # Pydantic serializes datetime → ISO string; the column is a DateTime
    # so accept both rather than the previous (broken) ``str | None``.
    created_at: datetime | None = None

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


def _textbook_dir(course_id: int) -> Path:
    """[TR-X2/X16] Resolve the upload dir for a course's textbooks.

    Uses ``settings.upload_dir`` (default ``./uploads``) and lives OUTSIDE
    ``backend/static`` so the public ``/static`` mount cannot serve uploaded
    files. Created on demand.
    """
    base = Path(get_settings().upload_dir).resolve() / "textbooks" / str(course_id)
    base.mkdir(parents=True, exist_ok=True)
    return base


def _safe_upload_filename(raw_filename: str) -> str:
    """[TR-X1/X3] Strip path components and prepend a random token.

    ``Path(name).name`` discards anything that looks like a directory
    component, defeating the ``../../etc/passwd`` style traversal. The
    8-byte token replaces the previous ``int(time.time())`` prefix that
    collided when two uploads landed in the same second.
    """
    base = Path(raw_filename or "unknown").name or "unknown"
    # Defense against null bytes / backslashes that some POSIX layers honor
    # but Path.name doesn't filter.
    base = base.replace("\x00", "").replace("\\", "_") or "unknown"
    return f"{secrets.token_hex(8)}_{base}"


class TextExtractionError(Exception):
    """[TR-X9] Raised when textbook content cannot be turned into usable text.

    The previous implementation returned in-band sentinel strings like
    ``"[PDF 文本提取失败: ...]"`` which downstream code happily stored as
    ``extracted_text`` and later fed to the LLM as if it were the textbook
    contents. Surfacing the failure as an exception lets the caller mark
    the row ``status='error'`` instead.
    """


def _extract_pdf(content: bytes) -> tuple[str, int]:
    """[TR-X15] Extract PDF text and page count in a single fitz.open pass.

    Returns ``(text, page_count)``. Raises :class:`TextExtractionError`
    if PyMuPDF is missing or fails to open the file.
    """
    try:
        import fitz  # PyMuPDF
        import io
    except ImportError as e:
        raise TextExtractionError("PyMuPDF 未安装，无法提取 PDF 文本") from e

    try:
        doc = fitz.open(stream=io.BytesIO(content), filetype="pdf")
    except Exception as e:
        raise TextExtractionError(f"无法打开 PDF：{e}") from e

    try:
        pages = [page.get_text() for page in doc]
        page_count = len(doc)
    finally:
        doc.close()

    text = "\n\n".join(pages).strip()
    if not text:
        raise TextExtractionError("PDF 文本提取结果为空（可能是扫描件 / 图片型 PDF）")
    return text, page_count


def _extract_epub(content: bytes) -> str:
    """[TR-X8/UNCERTAIN-3 A2] EPUB extraction via ebooklib + BeautifulSoup.

    Replaces the previous ``zipfile + regex`` approach which was both
    fragile (didn't honor EPUB spine ordering, dropped CSS-styled text)
    and unsafe (no zip-bomb protection on decompressed size).
    ``ebooklib`` parses through the spine in reading order and skips
    non-document items like NCX/cover.
    """
    try:
        import ebooklib  # noqa: F401 — needed for ITEM_DOCUMENT constant
        from ebooklib import epub
        from bs4 import BeautifulSoup
        import io
    except ImportError as e:
        raise TextExtractionError("ebooklib / beautifulsoup4 未安装") from e

    try:
        book = epub.read_epub(io.BytesIO(content))
    except Exception as e:
        raise TextExtractionError(f"无法打开 EPUB：{e}") from e

    parts: list[str] = []
    for item in book.get_items_of_type(ebooklib.ITEM_DOCUMENT):
        try:
            soup = BeautifulSoup(item.get_content(), "html.parser")
        except Exception:
            continue
        # get_text strips tags + collapses tags as separator; use newline so
        # paragraphs survive in the extracted text.
        text = soup.get_text(separator="\n").strip()
        if text:
            parts.append(text)

    full = "\n\n".join(parts).strip()
    if not full:
        raise TextExtractionError("EPUB 文本提取结果为空")
    return full


def _decode_text_file(content: bytes) -> str:
    """Try common Chinese / UTF-8 encodings for plain text uploads."""
    for encoding in ("utf-8", "gbk", "gb2312", "latin-1"):
        try:
            return content.decode(encoding)
        except (UnicodeDecodeError, LookupError):
            continue
    return content.decode("utf-8", errors="replace")


def _extract_text(content: bytes, filename: str) -> tuple[str, int | None]:
    """Dispatch to per-format extractor.

    Returns ``(text, page_count_or_None)``. Raises
    :class:`TextExtractionError` on any failure (X9). The previous
    function returned sentinel strings on failure; callers must now
    handle the exception explicitly.
    """
    ext = Path(filename).suffix.lower()

    if ext in {".txt", ".md", ".markdown"}:
        text = _decode_text_file(content)
        if not text.strip():
            raise TextExtractionError("文本文件内容为空")
        return text, None

    if ext == ".pdf":
        return _extract_pdf(content)

    if ext == ".epub":
        return _extract_epub(content), None

    raise TextExtractionError(f"不支持的文件类型: {ext}")


# Kept as a thin compat shim — older imports / tests reference this name.
def _extract_text_from_bytes(content: bytes, filename: str) -> str:
    """[TR-X9] Compat wrapper that returns just the text. New code should
    use ``_extract_text`` and handle :class:`TextExtractionError` directly."""
    text, _ = _extract_text(content, filename)
    return text


# ── API 端点 ──────────────────────────────────────────────────────────


async def _read_with_limit(file: UploadFile, limit: int) -> bytes:
    """[TR-X6] Stream the upload in chunks; abort the moment the cumulative
    size exceeds ``limit``.

    Reading the whole upload via ``await file.read()`` allocated up to
    ``limit`` bytes per request even when we'd reject the result a line
    later — multiple concurrent rogue uploads were a textbook OOM path.
    """
    chunks: list[bytes] = []
    total = 0
    chunk_size = 1 << 20  # 1 MiB
    while True:
        chunk = await file.read(chunk_size)
        if not chunk:
            break
        total += len(chunk)
        if total > limit:
            raise HTTPException(status_code=413, detail="文件超过 50MB 限制")
        chunks.append(chunk)
    return b"".join(chunks)


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
    from anyio import to_thread

    course = _get_course_with_auth(course_id, db, current_user)

    # 验证文件类型
    filename = file.filename or "unknown.txt"
    ext = Path(filename).suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=422,
            detail=f"不支持的文件类型 '{ext}'，允许: {', '.join(sorted(ALLOWED_EXTENSIONS))}",
        )

    # [TR-X6] Streaming size check — reject before allocating the whole file.
    content = await _read_with_limit(file, MAX_FILE_SIZE)

    # [TR-X2/X16] Store outside backend/static so the public /static mount
    # cannot serve uploaded files; access goes through GET /textbooks/{id}/file.
    upload_root = _textbook_dir(course_id)
    safe_name = _safe_upload_filename(filename)
    file_path = upload_root / safe_name

    # [TR-X1] Defense in depth: even after Path.name + token prefix, verify
    # the resolved path stays inside upload_root.
    resolved = file_path.resolve()
    if upload_root.resolve() not in resolved.parents:
        raise HTTPException(status_code=400, detail="非法文件名")

    file_path.write_bytes(content)

    # [TR-X7] Extraction is CPU-bound (PyMuPDF page traversal, lxml HTML
    # parsing for EPUB). Offload to a worker thread so the event loop stays
    # responsive for other requests during multi-MB uploads.
    # [TR-X9] Failures raise TextExtractionError; we record status='error'
    # instead of injecting sentinel strings into extracted_text.
    # [TR-X15] _extract_text returns (text, page_count) in one call.
    extracted_text: str | None = None
    page_count: int | None = None
    error_message: str | None = None
    status = "extracted"
    try:
        extracted_text, page_count = await to_thread.run_sync(
            _extract_text, content, filename,
        )
    except TextExtractionError as e:
        status = "error"
        error_message = str(e)
        logger.warning("textbook extraction failed for %s: %s", filename, e)

    # [TR-X4] If the DB write fails after we already wrote the file, tear
    # down the file so we don't leave orphans on disk.
    textbook = Textbook(
        course_id=course_id,
        user_id=current_user.id,
        filename=filename,
        file_path=str(file_path),
        file_size=len(content),
        content_type=file.content_type,
        extracted_text=extracted_text,
        page_count=page_count,
        status=status,
        error_message=error_message,
    )
    try:
        db.add(textbook)
        db.commit()
        db.refresh(textbook)
    except Exception:
        db.rollback()
        try:
            file_path.unlink(missing_ok=True)
        except OSError as cleanup_err:
            logger.warning(
                "textbook orphan cleanup failed (file=%s): %s",
                file_path, cleanup_err,
            )
        raise

    logger.info("教材上传成功: course_id=%d, textbook_id=%d, filename=%s, size=%d, status=%s",
                course_id, textbook.id, filename, len(content), status)

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


@router.get("/textbooks/{textbook_id}/file")
def download_textbook(
    textbook_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """[TR-X2] Auth-protected textbook file download.

    Replaces the previous behaviour where uploads landed in ``backend/static``
    and were served by the public StaticFiles mount with no auth check.
    Files now live in ``settings.upload_dir``; this endpoint validates
    ownership before streaming.
    """
    textbook = db.query(Textbook).filter(
        Textbook.id == textbook_id,
        Textbook.user_id == current_user.id,
    ).first()
    if not textbook:
        raise HTTPException(status_code=404, detail="教材不存在")

    file_path = Path(textbook.file_path)
    if not file_path.exists():
        # Row exists but file is gone (e.g., orphaned by an old failed
        # delete). Don't expose internal state — surface 404.
        logger.warning("textbook %d file missing on disk: %s", textbook_id, file_path)
        raise HTTPException(status_code=404, detail="教材文件不存在")

    return FileResponse(
        path=str(file_path),
        filename=textbook.filename,
        media_type=textbook.content_type or "application/octet-stream",
    )


@router.delete("/courses/{course_id}/textbooks/{textbook_id}", status_code=204)
def delete_textbook(
    course_id: int,
    textbook_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """[TR-X14] 204 No Content — no JSON body, OpenAPI now matches reality."""
    _get_course_with_auth(course_id, db, current_user)

    textbook = db.query(Textbook).filter(
        Textbook.id == textbook_id,
        Textbook.course_id == course_id,
        Textbook.user_id == current_user.id,
    ).first()
    if not textbook:
        raise HTTPException(status_code=404, detail="教材不存在")

    # [TR-X5] Delete the row and commit FIRST. The previous order (unlink →
    # DELETE → commit) left a ghost row pointing at a missing file when
    # commit failed. After commit succeeds, even an unlink failure is
    # benign — at worst a stray file on disk to clean up later.
    file_path = Path(textbook.file_path) if textbook.file_path else None
    db.delete(textbook)
    db.commit()

    if file_path is not None:
        try:
            file_path.unlink(missing_ok=True)
        except OSError as e:
            logger.warning("教材文件删除失败 (post-commit, file=%s): %s", file_path, e)


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

    # [TR-X11/UNCERTAIN-2] Reject regeneration once a course already has
    # generated content. course.meta also stores teaching progress
    # (current_lesson_index, completed_lessons) — silently overwriting
    # generated_lessons would invalidate that progress and confuse the
    # learner. The frontend must explicitly clear progress before regen
    # (separate endpoint, future work).
    existing_meta = course.meta or {}
    if existing_meta.get("generated_lessons"):
        raise HTTPException(
            status_code=409,
            detail=(
                "课程已生成内容，无法直接重新生成。"
                "请先清空课程进度（删除 generated_lessons 后再调用本接口）。"
            ),
        )

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

    # [TR-X12] Chapter-boundary truncation — keeps first N complete chapters,
    # drops the tail. The previous head+tail strategy lost the middle of the
    # textbook silently. (See docs/milestones/textbook-chunked-llm-pipeline.md
    # for the proper map-reduce solution.)
    all_text = _truncate_at_chapter_boundary(all_text, MAX_GENERATION_CHARS)

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

    # [TR-X10] Single commit. Previously two commits — between them, if the
    # second failed, textbooks were permanently marked 'processed' but the
    # course had no generated content, requiring users to delete + re-upload
    # textbooks to retry. One commit makes textbook status and course.meta
    # update atomically.
    for t in textbooks:
        t.status = "processed"

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
    return mastery_tracker.get_course_mastery(db, course_id, current_user.id)


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
