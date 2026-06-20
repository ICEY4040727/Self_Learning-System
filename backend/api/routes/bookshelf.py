"""书架 API — 用户级教材库

教材上传到书架后再关联到课程，解决"先有课程才能上传教材"的循环依赖。
支持：上传、列表、删除、关联到课程、从课程取消关联。
"""

import logging
import secrets
from contextlib import suppress
from datetime import datetime
from pathlib import Path

from fastapi import APIRouter, Body, Depends, HTTPException, UploadFile
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.orm import Session

from backend.api.routes.auth import get_current_user
from backend.api.routes.textbook import (
    ALLOWED_EXTENSIONS,
    TextExtractionError,
    _extract_text,
    _max_file_size,
    _read_with_limit,
    _safe_upload_filename,
)
from backend.core.config import get_settings
from backend.db.database import get_db
from backend.models.models import Course, Textbook, TextbookLibrary, User, World

logger = logging.getLogger(__name__)

router = APIRouter()


# ── Pydantic Schemas ──────────────────────────────────────────────────


class BookshelfItemResponse(BaseModel):
    id: int
    filename: str
    file_size: int | None = None
    content_type: str | None = None
    page_count: int | None = None
    status: str = "extracted"
    error_message: str | None = None
    is_usable: bool = False
    title: str | None = None
    created_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)


class BookshelfListResponse(BaseModel):
    """带有关联课程信息的书架教材列表"""
    id: int
    filename: str
    file_size: int | None = None
    content_type: str | None = None
    page_count: int | None = None
    status: str = "extracted"
    error_message: str | None = None
    is_usable: bool = False
    title: str | None = None
    created_at: datetime | None = None
    linked_course_ids: list[int] = Field(default_factory=list)

    model_config = ConfigDict(from_attributes=True)


class LinkToCourseRequest(BaseModel):
    library_id: int


# ── 工具函数 ──────────────────────────────────────────────────────────


def _library_dir() -> Path:
    """书架教材存储目录（用户级，不依赖 course_id）"""
    base = Path(get_settings().upload_dir).resolve() / "bookshelf"
    base.mkdir(parents=True, exist_ok=True)
    return base


# ── API 端点 ──────────────────────────────────────────────────────────


@router.post("/bookshelf/upload", response_model=BookshelfItemResponse)
async def upload_to_bookshelf(
    file: UploadFile,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """上传教材到书架（用户级，无需课程 ID）"""
    from anyio import to_thread

    # 验证文件类型
    filename = file.filename or "unknown.txt"
    ext = Path(filename).suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=422,
            detail=f"不支持的文件类型 '{ext}'，允许: {', '.join(sorted(ALLOWED_EXTENSIONS))}",
        )

    # 流式读取，带大小限制
    content = await _read_with_limit(file, _max_file_size())

    # 安全存储
    upload_root = _library_dir()
    safe_name = _safe_upload_filename(filename)
    file_path = upload_root / safe_name

    resolved = file_path.resolve()
    if upload_root.resolve() not in resolved.parents:
        raise HTTPException(status_code=400, detail="非法文件名")

    file_path.write_bytes(content)

    # 提取文本
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
        logger.warning("bookshelf extraction failed for %s: %s", filename, e)

    item = TextbookLibrary(
        user_id=current_user.id,
        filename=filename,
        file_path=str(file_path),
        file_size=len(content),
        content_type=file.content_type,
        extracted_text=extracted_text,
        page_count=page_count,
        status=status,
        error_message=error_message,
        title=filename,  # 默认标题为文件名
    )
    try:
        db.add(item)
        db.commit()
        db.refresh(item)
    except Exception:
        db.rollback()
        with suppress(OSError):
            file_path.unlink(missing_ok=True)
        raise

    logger.info("书架教材上传成功: user_id=%d, library_id=%d, filename=%s",
                current_user.id, item.id, filename)

    return item


@router.get("/bookshelf", response_model=list[BookshelfListResponse])
def list_bookshelf(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """列出当前用户书架中的所有教材，附带关联的课程 ID"""
    items = db.query(TextbookLibrary).filter(
        TextbookLibrary.user_id == current_user.id,
    ).order_by(TextbookLibrary.created_at.desc()).all()

    result = []
    for item in items:
        # 查找关联了此教材的课程（通过 extracted_text 匹配或文件名匹配不可靠，
        # 所以我们在 Textbook 表上加 library_id 字段来追踪关联）
        linked_courses = db.query(Textbook.course_id).filter(
            Textbook.user_id == current_user.id,
            Textbook.library_id == item.id,
        ).distinct().order_by(Textbook.course_id).all()
        linked_course_ids = [c[0] for c in linked_courses]

        result.append(BookshelfListResponse(
            id=item.id,
            filename=item.filename,
            file_size=item.file_size,
            content_type=item.content_type,
            page_count=item.page_count,
            status=item.status,
            error_message=item.error_message,
            title=item.title,
            created_at=item.created_at,
            linked_course_ids=linked_course_ids,
        ))

    return result


@router.delete("/bookshelf/{library_id}", status_code=204)
def delete_from_bookshelf(
    library_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """从书架删除教材（同时删除文件）"""
    item = db.query(TextbookLibrary).filter(
        TextbookLibrary.id == library_id,
        TextbookLibrary.user_id == current_user.id,
    ).first()
    if not item:
        raise HTTPException(status_code=404, detail="书架教材不存在")

    linked_course_ids = [
        row[0]
        for row in db.query(Textbook.course_id).filter(
            Textbook.user_id == current_user.id,
            Textbook.library_id == item.id,
        ).distinct().order_by(Textbook.course_id).all()
    ]
    if linked_course_ids:
        raise HTTPException(
            status_code=409,
            detail={
                "message": "教材已被课程引用，请先在课程中移除关联",
                "linked_course_ids": linked_course_ids,
            },
        )

    file_path = Path(item.file_path) if item.file_path else None
    db.delete(item)
    db.commit()

    if file_path is not None:
        try:
            file_path.unlink(missing_ok=True)
        except OSError as e:
            logger.warning("书架文件删除失败 (file=%s): %s", file_path, e)


@router.post("/courses/{course_id}/link-textbook", status_code=201)
def link_textbook_to_course(
    course_id: int,
    req: LinkToCourseRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """将书架教材关联到课程（创建 Textbook 记录引用书架文件）"""
    # 验证课程权限
    course = db.query(Course).join(World, Course.world_id == World.id).filter(
        Course.id == course_id,
        World.user_id == current_user.id,
    ).first()
    if not course:
        raise HTTPException(status_code=404, detail="课程不存在")

    # 验证书架教材
    lib_item = db.query(TextbookLibrary).filter(
        TextbookLibrary.id == req.library_id,
        TextbookLibrary.user_id == current_user.id,
    ).first()
    if not lib_item:
        raise HTTPException(status_code=404, detail="书架教材不存在")

    if not lib_item.is_usable:
        raise HTTPException(status_code=400, detail="教材文本提取失败，无法关联")

    # 检查是否已经关联
    existing = db.query(Textbook).filter(
        Textbook.course_id == course_id,
        Textbook.library_id == lib_item.id,
        Textbook.user_id == current_user.id,
    ).first()
    if existing:
        raise HTTPException(status_code=409, detail="该教材已经关联到此课程")

    # 创建 Textbook 记录（引用书架文件）
    textbook = Textbook(
        course_id=course_id,
        user_id=current_user.id,
        library_id=lib_item.id,
        filename=lib_item.filename,
        file_path=lib_item.file_path,
        file_size=lib_item.file_size,
        content_type=lib_item.content_type,
        owns_file=False,
        extracted_text=lib_item.extracted_text,
        page_count=lib_item.page_count,
        status="extracted",
    )
    db.add(textbook)
    db.commit()
    db.refresh(textbook)

    logger.info("书架教材关联课程: library_id=%d → course_id=%d, textbook_id=%d",
                req.library_id, course_id, textbook.id)

    return {"textbook_id": textbook.id, "library_id": req.library_id, "course_id": course_id}


@router.post("/courses/batch-link-textbooks")
def batch_link_textbooks(
    course_id: int,
    library_ids: list[int] = Body(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """批量将书架教材关联到课程，返回创建的 Textbook ID 列表"""
    # 验证课程权限
    course = db.query(Course).join(World, Course.world_id == World.id).filter(
        Course.id == course_id,
        World.user_id == current_user.id,
    ).first()
    if not course:
        raise HTTPException(status_code=404, detail="课程不存在")

    if not library_ids:
        raise HTTPException(status_code=400, detail="必须选择至少一个教材")

    results = []
    for lib_id in library_ids:
        lib_item = db.query(TextbookLibrary).filter(
            TextbookLibrary.id == lib_id,
            TextbookLibrary.user_id == current_user.id,
        ).first()
        if not lib_item:
            raise HTTPException(status_code=404, detail=f"书架教材 {lib_id} 不存在")

        if not lib_item.is_usable:
            raise HTTPException(status_code=400, detail=f"教材 '{lib_item.filename}' 文本提取失败，无法关联")

        # 检查重复
        existing = db.query(Textbook).filter(
            Textbook.course_id == course_id,
            Textbook.library_id == lib_item.id,
            Textbook.user_id == current_user.id,
        ).first()
        if existing:
            results.append({"textbook_id": existing.id, "library_id": lib_id, "skipped": True})
            continue

        textbook = Textbook(
            course_id=course_id,
            user_id=current_user.id,
            library_id=lib_item.id,
            filename=lib_item.filename,
            file_path=lib_item.file_path,
            file_size=lib_item.file_size,
            content_type=lib_item.content_type,
            owns_file=False,
            extracted_text=lib_item.extracted_text,
            page_count=lib_item.page_count,
            status="extracted",
        )
        db.add(textbook)
        db.flush()
        results.append({"textbook_id": textbook.id, "library_id": lib_id, "skipped": False})

    db.commit()
    return results

