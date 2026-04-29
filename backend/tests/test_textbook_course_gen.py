"""Tests for Phase 3 Step 2: 教材上传 + AI 课程生成

验证:
1. Textbook 模型创建和关联
2. 文本提取 (_extract_text_from_bytes)
3. CourseGenerator JSON 解析与验证
4. CourseGenerateResponse 结构
"""

import pytest

from backend.models.models import Course, Textbook, World


# ─── 1. Textbook 模型 ───


class TestTextbookModel:
    """验证 Textbook 模型基本功能"""

    def test_create_textbook(self, db_session):
        """可以创建 Textbook 并关联到 Course"""
        world = World(user_id=1, name="测试世界")
        db_session.add(world)
        db_session.flush()

        course = Course(world_id=world.id, name="测试课程")
        db_session.add(course)
        db_session.flush()

        tb = Textbook(
            course_id=course.id,
            user_id=1,
            filename="test.pdf",
            file_path="/tmp/test.pdf",
            file_size=1024,
            status="extracted",
            extracted_text="这是一个测试教材的内容。",
        )
        db_session.add(tb)
        db_session.commit()

        assert tb.id is not None
        assert tb.course_id == course.id
        assert tb.status == "extracted"
        assert tb.extracted_text is not None

    def test_textbook_course_relationship(self, db_session):
        """Course.textbooks 关系正确"""
        world = World(user_id=1, name="测试世界")
        db_session.add(world)
        db_session.flush()

        course = Course(world_id=world.id, name="测试课程")
        db_session.add(course)
        db_session.flush()

        tb1 = Textbook(course_id=course.id, user_id=1, filename="a.txt", file_path="/tmp/a.txt")
        tb2 = Textbook(course_id=course.id, user_id=1, filename="b.txt", file_path="/tmp/b.txt")
        db_session.add_all([tb1, tb2])
        db_session.commit()

        assert len(course.textbooks) == 2

    def test_textbook_default_status(self, db_session):
        """默认状态为 'uploaded'"""
        world = World(user_id=1, name="测试世界")
        db_session.add(world)
        db_session.flush()

        course = Course(world_id=world.id, name="测试课程")
        db_session.add(course)
        db_session.flush()

        tb = Textbook(
            course_id=course.id, user_id=1,
            filename="test.txt", file_path="/tmp/test.txt",
        )
        db_session.add(tb)
        db_session.commit()

        assert tb.status == "uploaded"


# ─── 2. 文本提取 ───


class TestTextExtraction:
    """验证 _extract_text_from_bytes"""

    def test_extract_txt_utf8(self):
        """正确提取 UTF-8 文本"""
        from backend.api.routes.textbook import _extract_text_from_bytes

        content = "这是中文测试内容\n第二行".encode("utf-8")
        result = _extract_text_from_bytes(content, "test.txt")
        assert "中文测试" in result
        assert "第二行" in result

    def test_extract_txt_gbk(self):
        """正确提取 GBK 编码文本"""
        from backend.api.routes.textbook import _extract_text_from_bytes

        content = "这是GBK编码的文本".encode("gbk")
        result = _extract_text_from_bytes(content, "test.txt")
        assert "GBK" in result

    def test_extract_md(self):
        """正确提取 Markdown 文本"""
        from backend.api.routes.textbook import _extract_text_from_bytes

        content = b"# Title\n\nSome **bold** text"
        result = _extract_text_from_bytes(content, "notes.md")
        assert "Title" in result
        assert "bold" in result

    def test_extract_markdown_ext(self):
        """支持 .markdown 扩展名"""
        from backend.api.routes.textbook import _extract_text_from_bytes

        content = b"Markdown content here"
        result = _extract_text_from_bytes(content, "notes.markdown")
        assert "Markdown content" in result

    def test_unsupported_extension_raises(self):
        """[TR-X9] 不支持的扩展名 → TextExtractionError（旧版返回 sentinel string，
        会被当作正常文本入库）"""
        from backend.api.routes.textbook import _extract_text_from_bytes, TextExtractionError

        with pytest.raises(TextExtractionError, match="不支持"):
            _extract_text_from_bytes(b"content", "file.docx")


# ─── 3. CourseGenerator 解析 ───


class TestCourseGeneratorParsing:
    """验证 CourseGenerator 的 JSON 解析和验证"""

    def test_parse_clean_json(self):
        """正确解析干净的 JSON"""
        from backend.services.course_generator import CourseGenerator

        gen = CourseGenerator()
        raw = '{"overview": "测试课程", "lessons": [{"title": "L1", "description": "D1", "order": 1, "concepts": ["c1"]}], "concept_map": null}'
        result = gen._parse_response(raw)

        assert result["overview"] == "测试课程"
        assert len(result["lessons"]) == 1

    def test_parse_json_with_markdown_block(self):
        """正确解析带 markdown 代码块的 JSON"""
        from backend.services.course_generator import CourseGenerator

        gen = CourseGenerator()
        raw = '```json\n{"overview": "测试", "lessons": []}\n```'
        result = gen._parse_response(raw)

        assert result["overview"] == "测试"

    def test_parse_json_with_extra_text(self):
        """正确解析前后有额外文本的 JSON"""
        from backend.services.course_generator import CourseGenerator

        gen = CourseGenerator()
        raw = '这是课程设计结果：\n{"overview": "数学", "lessons": []}\n希望对你有帮助！'
        result = gen._parse_response(raw)

        assert result["overview"] == "数学"

    def test_parse_invalid_json_raises(self):
        """无效 JSON 抛出 ValueError"""
        from backend.services.course_generator import CourseGenerator

        gen = CourseGenerator()
        with pytest.raises(ValueError, match="JSON"):
            gen._parse_response("this is not json at all")

    def test_validate_result_empty_raises(self):
        """[TODO-T4] Empty lessons must raise — silent fallback to a fake
        '入门' lesson hid LLM failures from the user."""
        from backend.services.course_generator import CourseGenerator

        gen = CourseGenerator()
        with pytest.raises(ValueError, match="未生成有效章节"):
            gen._validate_result({})

    def test_validate_result_normalizes_lessons(self):
        """验证 lessons 被标准化为 GeneratedLesson"""
        from backend.services.course_generator import CourseGenerator

        gen = CourseGenerator()
        data = {
            "overview": "Python 入门",
            "lessons": [
                {"title": "变量", "description": "学习变量", "order": 1, "concepts": ["变量", "赋值"]},
                {"title": "循环", "description": "学习循环", "order": 2, "concepts": ["for", "while"], "prerequisites": ["变量"]},
            ],
            "concept_map": {"nodes": [], "edges": []},
        }
        result = gen._validate_result(data)

        assert result["overview"] == "Python 入门"
        assert len(result["lessons"]) == 2
        assert result["lessons"][0].title == "变量"
        assert result["lessons"][1].prerequisites == ["变量"]
        assert result["concept_map"] == {"nodes": [], "edges": []}

    def test_validate_result_skips_bad_lessons(self):
        """跳过格式错误的 lesson"""
        from backend.services.course_generator import CourseGenerator

        gen = CourseGenerator()
        data = {
            "lessons": [
                {"title": "OK", "description": "", "order": 1, "concepts": []},
                "not a dict",
                42,
            ]
        }
        result = gen._validate_result(data)
        assert len(result["lessons"]) == 1


# ─── 4. CourseGenerator Prompt 拼装 ───


class TestCourseGeneratorPrompt:
    """验证 prompt 拼装逻辑"""

    def test_generate_prompt_basic(self):
        """基本 prompt 拼装正确"""
        from backend.services.course_generator import COURSE_GENERATION_USER_TEMPLATE

        prompt = COURSE_GENERATION_USER_TEMPLATE.format(
            course_name="Python基础",
            course_description="学习Python编程",
            target_level="入门",
            custom_instructions="",
            target_days="",
            text="变量是存储数据的容器...",
        )

        assert "Python基础" in prompt
        assert "学习Python编程" in prompt
        assert "变量是存储数据的容器" in prompt

    def test_generate_prompt_with_custom_instructions(self):
        """自定义指令正确拼入"""
        from backend.services.course_generator import COURSE_GENERATION_USER_TEMPLATE

        prompt = COURSE_GENERATION_USER_TEMPLATE.format(
            course_name="测试",
            course_description="无",
            target_level="未指定",
            custom_instructions="\n- 自定义指令: 侧重实践",
            target_days="",
            text="内容",
        )

        assert "侧重实践" in prompt

    def test_generate_prompt_with_target_days(self):
        """目标天数正确拼入"""
        from backend.services.course_generator import COURSE_GENERATION_USER_TEMPLATE

        prompt = COURSE_GENERATION_USER_TEMPLATE.format(
            course_name="测试",
            course_description="无",
            target_level="未指定",
            custom_instructions="",
            target_days="\n- 目标学习天数: 30天",
            text="内容",
        )


# ─── 5. Storage / Filename safety (TR-X1, X3) ───


class TestSafeUploadFilename:
    """[TR-X1/X3] _safe_upload_filename strips path components + random prefix."""

    def test_strips_path_traversal(self):
        from backend.api.routes.textbook import _safe_upload_filename

        result = _safe_upload_filename("../../../etc/passwd.pdf")
        # token_hex(8) = 16 hex chars + "_" + base name
        assert "/" not in result
        assert ".." not in result
        assert result.endswith("_passwd.pdf")

    def test_strips_backslashes(self):
        from backend.api.routes.textbook import _safe_upload_filename

        result = _safe_upload_filename("..\\..\\Windows\\evil.pdf")
        assert "\\" not in result
        # Path.name on POSIX treats `..\..\Windows\evil.pdf` as a single
        # component — the filter then replaces backslashes with `_`.
        assert "evil.pdf" in result

    def test_unique_prefix_avoids_collision(self):
        """[TR-X3] 同一秒上传同名文件应得到不同的 safe_name。"""
        from backend.api.routes.textbook import _safe_upload_filename

        a = _safe_upload_filename("notes.md")
        b = _safe_upload_filename("notes.md")
        assert a != b
        assert a.endswith("_notes.md")
        assert b.endswith("_notes.md")

    def test_handles_empty_filename(self):
        from backend.api.routes.textbook import _safe_upload_filename

        result = _safe_upload_filename("")
        assert "unknown" in result


# ─── 6. Extraction error handling (TR-X9) ───


class TestExtractionErrorHandling:
    """[TR-X9] _extract_text raises TextExtractionError instead of returning
    sentinel strings that would silently land in extracted_text."""

    def test_invalid_pdf_raises(self):
        from backend.api.routes.textbook import _extract_text, TextExtractionError

        with pytest.raises(TextExtractionError):
            _extract_text(b"this is not a pdf", "fake.pdf")

    def test_invalid_epub_raises(self):
        from backend.api.routes.textbook import _extract_text, TextExtractionError

        with pytest.raises(TextExtractionError):
            _extract_text(b"this is not an epub", "fake.epub")

    def test_empty_text_file_raises(self):
        from backend.api.routes.textbook import _extract_text, TextExtractionError

        with pytest.raises(TextExtractionError):
            _extract_text(b"   \n\n  ", "empty.txt")

    def test_pdf_returns_text_and_page_count(self):
        """Make a tiny PDF with PyMuPDF and round-trip it."""
        import fitz
        import io

        doc = fitz.open()  # empty document
        page = doc.new_page()
        page.insert_text((50, 100), "Hello textbook")
        buf = io.BytesIO()
        doc.save(buf)
        doc.close()

        from backend.api.routes.textbook import _extract_text
        text, pages = _extract_text(buf.getvalue(), "tiny.pdf")
        assert "Hello textbook" in text
        assert pages == 1


# ─── 7. Chapter-boundary truncation (TR-X12) ───


class TestChapterBoundaryTruncation:
    """[TR-X12] _truncate_at_chapter_boundary keeps complete chapters from
    the head, drops the tail — never cuts to the middle of content."""

    def test_under_limit_unchanged(self):
        from backend.api.routes.textbook import _truncate_at_chapter_boundary
        text = "short content"
        assert _truncate_at_chapter_boundary(text, 1000) == text

    def test_chinese_chapter_boundary(self):
        from backend.api.routes.textbook import _truncate_at_chapter_boundary
        text = (
            "前言内容...\n"
            "第一章 概念\n" + "x" * 100 + "\n"
            "第二章 进阶\n" + "y" * 100 + "\n"
            "第三章 应用\n" + "z" * 100
        )
        # Limit just past second chapter heading but before third
        # (~140 chars in)
        result = _truncate_at_chapter_boundary(text, 140)
        assert "第一章" in result
        assert "第二章" not in result, "third-chapter region must be dropped"

    def test_markdown_heading_boundary(self):
        from backend.api.routes.textbook import _truncate_at_chapter_boundary
        text = (
            "intro\n"
            "# Section 1\n" + "a" * 50 + "\n"
            "## Subsection\n" + "b" * 50 + "\n"
            "# Section 2\n" + "c" * 50
        )
        result = _truncate_at_chapter_boundary(text, 100)
        # Should cut at "# Section 2" (the last heading within the first 100 chars)
        # NOT at any earlier heading and NOT in the middle of content.
        assert "Section 2" not in result
        assert "Section 1" in result

    def test_english_chapter_boundary(self):
        from backend.api.routes.textbook import _truncate_at_chapter_boundary
        text = (
            "Preamble...\n"
            "Chapter 1 Variables\n" + "v" * 50 + "\n"
            "Chapter 2 Loops\n" + "l" * 50
        )
        result = _truncate_at_chapter_boundary(text, 70)
        assert "Chapter 1" in result
        assert "Chapter 2" not in result

    def test_no_chapter_falls_back_to_hard_cut(self):
        from backend.api.routes.textbook import _truncate_at_chapter_boundary
        text = "x" * 200  # No chapter structure
        result = _truncate_at_chapter_boundary(text, 100)
        assert len(result) == 100


# ─── 8. End-to-end TestClient routes (TR-X1, X2, X11) ───


class TestTextbookRoutes:
    """[TR-X17] Auth + safety regression tests via the FastAPI TestClient."""

    def _setup_user_world_course(self, client, auth_headers, tmp_path, monkeypatch):
        """Helper: redirect uploads to tmp_path, create world + course."""
        from backend.core.config import get_settings
        s = get_settings()
        # Override upload dir for this test only
        monkeypatch.setattr(s, "upload_dir", str(tmp_path), raising=False)
        # Clear lru_cache so the new upload_dir takes effect inside the route
        get_settings.cache_clear()
        # Restore via env var so cache_clear in subsequent tests gets a clean settings
        monkeypatch.setenv("UPLOAD_DIR", str(tmp_path))

        world = client.post("/api/worlds", json={"name": "W"}, headers=auth_headers).json()
        course = client.post(
            "/api/courses",
            json={"world_id": world["id"], "name": "C"},
            headers=auth_headers,
        ).json()
        return world, course

    def test_upload_strips_path_traversal_filename(
        self, client, auth_headers, tmp_path, monkeypatch,
    ):
        """[TR-X1] Filename like '../../etc/passwd.pdf' must not escape upload dir."""
        _, course = self._setup_user_world_course(client, auth_headers, tmp_path, monkeypatch)

        # Build a tiny valid PDF for the upload
        import fitz
        import io
        doc = fitz.open()
        doc.new_page().insert_text((50, 100), "ok")
        buf = io.BytesIO()
        doc.save(buf)
        doc.close()

        evil_filename = "../../../etc/passwd.pdf"
        resp = client.post(
            f"/api/courses/{course['id']}/textbooks",
            headers=auth_headers,
            files={"file": (evil_filename, buf.getvalue(), "application/pdf")},
        )
        assert resp.status_code == 200, resp.text
        data = resp.json()
        # The DB row preserves the original filename for display
        assert data["filename"] == evil_filename
        # But the on-disk path must live under tmp_path
        from backend.models.models import Textbook
        from sqlalchemy.orm import sessionmaker
        from backend.db.database import get_db
        # Pull the row directly to inspect file_path (not exposed via API).
        # The conftest db_session fixture is the same session the route used,
        # so query through the dependency.
        # Easier: use a fresh query
        from pathlib import Path as _P
        # The TestClient and the test share the same SessionLocal via fixture
        from backend.tests.conftest import TestSessionLocal
        with TestSessionLocal() as s:
            tb = s.query(Textbook).filter_by(id=data["id"]).one()
            disk_path = _P(tb.file_path).resolve()
            assert _P(tmp_path).resolve() in disk_path.parents, \
                f"file written outside upload dir: {disk_path}"
            assert "passwd.pdf" in disk_path.name  # original name preserved (sans path)

    def test_download_endpoint_requires_auth(
        self, client, auth_headers, tmp_path, monkeypatch,
    ):
        """[TR-X2] Anonymous request to /textbooks/{id}/file → 401."""
        _, course = self._setup_user_world_course(client, auth_headers, tmp_path, monkeypatch)
        import fitz, io
        doc = fitz.open(); doc.new_page().insert_text((50, 100), "x")
        buf = io.BytesIO(); doc.save(buf); doc.close()
        upload = client.post(
            f"/api/courses/{course['id']}/textbooks",
            headers=auth_headers,
            files={"file": ("notes.pdf", buf.getvalue(), "application/pdf")},
        ).json()

        # No Authorization header
        resp = client.get(f"/api/textbooks/{upload['id']}/file")
        assert resp.status_code == 401, resp.text

        # With auth → 200
        resp = client.get(f"/api/textbooks/{upload['id']}/file", headers=auth_headers)
        assert resp.status_code == 200
        # Content-Disposition advertises the original filename
        assert "notes.pdf" in resp.headers.get("content-disposition", "")

    def test_download_endpoint_blocks_other_users(
        self, client, auth_headers, tmp_path, monkeypatch,
    ):
        """[TR-X2] Another user calling /textbooks/{id}/file → 404 (not 200)."""
        _, course = self._setup_user_world_course(client, auth_headers, tmp_path, monkeypatch)
        import fitz, io
        doc = fitz.open(); doc.new_page().insert_text((50, 100), "x")
        buf = io.BytesIO(); doc.save(buf); doc.close()
        upload = client.post(
            f"/api/courses/{course['id']}/textbooks",
            headers=auth_headers,
            files={"file": ("notes.pdf", buf.getvalue(), "application/pdf")},
        ).json()

        # Register a second user (username min 3 chars)
        client.post("/api/auth/register", json={"username": "user2", "password": "p2pwd1234"})
        login = client.post(
            "/api/auth/login",
            data={"username": "user2", "password": "p2pwd1234"},
        ).json()
        other_headers = {"Authorization": f"Bearer {login['access_token']}"}

        resp = client.get(f"/api/textbooks/{upload['id']}/file", headers=other_headers)
        assert resp.status_code == 404, "owner-mismatch must surface as 404, not leak content"

    def test_regenerate_rejected_when_lessons_exist(
        self, client, auth_headers, tmp_path, monkeypatch,
    ):
        """[TR-X11/UNCERTAIN-2] Second /generate call → 409 once meta has
        generated_lessons (course progress would otherwise be invalidated)."""
        _, course = self._setup_user_world_course(client, auth_headers, tmp_path, monkeypatch)

        # Seed course.meta directly to simulate prior generate
        from backend.tests.conftest import TestSessionLocal
        from backend.models.models import Course
        from sqlalchemy.orm.attributes import flag_modified
        with TestSessionLocal() as s:
            c = s.query(Course).filter_by(id=course["id"]).one()
            c.meta = {
                "generated_lessons": [{"title": "L1", "concepts": ["a"]}],
                "current_lesson_index": 0,
                "completed_lessons": [],
            }
            flag_modified(c, "meta")
            s.commit()

        resp = client.post(
            f"/api/courses/{course['id']}/generate",
            json={"course_id": course["id"]},
            headers=auth_headers,
        )
        assert resp.status_code == 409, resp.text
        assert "重新生成" in resp.text or "regenerate" in resp.text.lower() or "已生成" in resp.text
