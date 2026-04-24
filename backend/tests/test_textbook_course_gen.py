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

    def test_unsupported_extension(self):
        """不支持的扩展名返回提示"""
        from backend.api.routes.textbook import _extract_text_from_bytes

        result = _extract_text_from_bytes(b"content", "file.docx")
        assert "不支持" in result


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

    def test_validate_result_minimal(self):
        """最小输入生成默认课程"""
        from backend.services.course_generator import CourseGenerator

        gen = CourseGenerator()
        result = gen._validate_result({})

        assert result["overview"] == ""
        assert len(result["lessons"]) == 1  # 默认入门课
        assert result["concept_map"] is None

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
