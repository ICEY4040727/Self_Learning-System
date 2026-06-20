"""Tests for the textbook-first learning plan draft flow."""

from pathlib import Path

import pytest

from backend.core.config import get_settings
from backend.models.models import Course, LessonPlan, Textbook, World


@pytest.fixture
def upload_dir(tmp_path, monkeypatch):
    monkeypatch.setenv("UPLOAD_DIR", str(tmp_path))
    get_settings.cache_clear()
    yield tmp_path
    get_settings.cache_clear()


def _upload_textbook(client, auth_headers):
    content = """
# 第一章 博弈论导论
博弈论研究多个决策者之间的策略互动。核心概念包括参与者、策略、收益。
例题：判断囚徒困境中的参与者和策略。

# 第二章 纳什均衡
纳什均衡描述没有参与者愿意单方面改变策略的状态。
练习：给定收益矩阵，找出所有纳什均衡。
注意：不要把占优策略和纳什均衡混淆。
""".strip()
    resp = client.post(
        "/api/bookshelf/upload",
        headers=auth_headers,
        files={"file": ("game_theory.md", content.encode("utf-8"), "text/markdown")},
    )
    assert resp.status_code == 200
    payload = resp.json()
    assert payload["is_usable"] is True
    return payload["id"]


def test_create_learning_plan_draft_from_bookshelf_material(client, auth_headers, upload_dir):
    library_id = _upload_textbook(client, auth_headers)

    resp = client.post(
        "/api/learning-plans/drafts",
        headers=auth_headers,
        json={
            "material_ids": [library_id],
            "goal": "三个月内掌握博弈论，能应对考试和面试。",
            "course_form": {"name": "博弈论入门"},
        },
    )

    assert resp.status_code == 200
    payload = resp.json()
    assert payload["stage"] == "blueprint"
    assert payload["material_ids"] == [library_id]
    assert payload["material_analysis"]["chapter_tree"]
    assert payload["knowledge_blueprint"]["concepts"]
    assert payload["knowledge_blueprint"]["exercises"]
    assert payload["course_blueprint"]["course_title"] == "博弈论入门"
    assert payload["course_blueprint"]["route_type"] == "exam_sprint"
    assert payload["course_narrative_plan"]["route_bible"]["boundaries"]
    assert "world_plan" not in payload


def test_commit_learning_plan_draft_creates_existing_world_course_records(
    client,
    auth_headers,
    db_session,
    upload_dir,
):
    library_id = _upload_textbook(client, auth_headers)
    draft_resp = client.post(
        "/api/learning-plans/drafts",
        headers=auth_headers,
        json={
            "material_ids": [library_id],
            "goal": "系统理解博弈论并能做收益矩阵题。",
            "course_form": {"name": "博弈论路线"},
        },
    )
    draft_id = draft_resp.json()["id"]

    commit_resp = client.post(
        f"/api/learning-plans/drafts/{draft_id}/commit",
        headers=auth_headers,
        json={"target_level": "apply"},
    )

    assert commit_resp.status_code == 200
    committed = commit_resp.json()
    assert committed["lesson_count"] >= 2
    assert committed["linked_textbook_count"] == 1

    world = db_session.query(World).filter(World.id == committed["world_id"]).one()
    course = db_session.query(Course).filter(Course.id == committed["course_id"]).one()
    lessons = db_session.query(LessonPlan).filter(LessonPlan.course_id == course.id).all()
    textbooks = db_session.query(Textbook).filter(Textbook.course_id == course.id).all()

    assert world.user_id == course.world.user_id
    assert course.world_id == world.id
    assert course.meta["setup_flow"] == "textbook_first_v1"
    assert course.meta["knowledge_blueprint"]["concepts"]
    assert course.meta["course_narrative_plan"]["route_bible"]["boundaries"]
    assert len(lessons) == committed["lesson_count"]
    assert textbooks[0].library_id == library_id
    assert textbooks[0].owns_file is False


def test_update_world_layer_after_course_commit(client, auth_headers, db_session, upload_dir):
    library_id = _upload_textbook(client, auth_headers)
    draft_resp = client.post(
        "/api/learning-plans/drafts",
        headers=auth_headers,
        json={
            "material_ids": [library_id],
            "goal": "用三国策略世界学习博弈论。",
            "course_form": {"name": "博弈论策略课"},
        },
    )
    draft_id = draft_resp.json()["id"]
    commit_resp = client.post(f"/api/learning-plans/drafts/{draft_id}/commit", headers=auth_headers, json={})
    world_id = commit_resp.json()["world_id"]

    update_resp = client.put(
        f"/api/learning-plans/drafts/{draft_id}/world",
        headers=auth_headers,
        json={
            "world": {
                "name": "赤壁策略推演局",
                "premise": "用三国谋略包装博弈论学习，但所有事件必须回到教材蓝图。",
            },
            "route_bible": {
                "main_arc": "从囚徒困境走向纳什均衡推演。",
                "boundaries": ["剧情不得替代教材检查"],
            },
        },
    )

    assert update_resp.status_code == 200
    payload = update_resp.json()
    assert payload["course_narrative_plan"]["route_bible"]["boundaries"] == ["剧情不得替代教材检查"]
    assert "world_plan" not in payload
    world = db_session.query(World).filter(World.id == world_id).one()
    course = db_session.query(Course).filter(Course.id == commit_resp.json()["course_id"]).one()
    assert world.name == "赤壁策略推演局"
    assert course.meta["course_narrative_plan"]["route_bible"]["boundaries"] == ["剧情不得替代教材检查"]
