"""Tests for Course APIs - Issue #188

测试 3 个 Course 相关 API:
- GET /courses/{id}/sages
- GET /courses/{id}/sessions
- GET /courses/{id}/memory-facts
"""

from sqlalchemy.orm import Session

from backend.models.models import (
    MemoryFact,
)


class TestCourseSagesAPI:
    """测试 /courses/{course_id}/sages 端点"""

    def test_get_course_sages_returns_world_level_sages(self, client, auth_headers):
        """验证返回世界级别的 Sage 角色"""
        # 创建测试数据
        world_resp = client.post("/api/archive/worlds", json={"name": "TestWorld"}, headers=auth_headers)
        world_id = world_resp.json()["id"]

        # 创建 Sage 角色并绑定到世界
        sage_resp = client.post("/api/archive/character", json={
            "name": "TestSage",
            "type": "sage",
            "title": "导师"
        }, headers=auth_headers)
        sage_id = sage_resp.json()["id"]

        # 绑定到世界
        client.post(f"/api/archive/worlds/{world_id}/characters", json={
            "character_id": sage_id,
            "role": "sage",
            "is_primary": True
        }, headers=auth_headers)

        # 创建课程
        course_resp = client.post(f"/api/archive/worlds/{world_id}/courses", json={
            "name": "TestCourse"
        }, headers=auth_headers)
        course_id = course_resp.json()["id"]

        # 调用 API
        resp = client.get(f"/api/archive/courses/{course_id}/sages", headers=auth_headers)

        assert resp.status_code == 200
        sages = resp.json()
        assert len(sages) >= 1
        assert any(s["id"] == sage_id for s in sages)

    def test_get_course_sages_returns_meta_sage_ids(self, client, auth_headers):
        """验证优先从 meta.sage_ids 获取"""
        # 创建测试数据
        world_resp = client.post("/api/archive/worlds", json={"name": "TestWorld2"}, headers=auth_headers)
        world_id = world_resp.json()["id"]

        # 创建多个 Sage
        sage1_resp = client.post("/api/archive/character", json={
            "name": "Sage1", "type": "sage"
        }, headers=auth_headers)
        sage1_id = sage1_resp.json()["id"]

        sage2_resp = client.post("/api/archive/character", json={
            "name": "Sage2", "type": "sage"
        }, headers=auth_headers)
        sage2_id = sage2_resp.json()["id"]

        # 绑定第一个 Sage 到世界
        client.post(f"/api/archive/worlds/{world_id}/characters", json={
            "character_id": sage1_id,
            "role": "sage",
            "is_primary": True
        }, headers=auth_headers)

        # 创建课程，指定 sage_ids
        course_resp = client.post(f"/api/archive/worlds/{world_id}/courses", json={
            "name": "CourseWithMeta",
            "meta": {"sage_ids": [sage1_id, sage2_id]}
        }, headers=auth_headers)
        course_id = course_resp.json()["id"]

        # 调用 API
        resp = client.get(f"/api/archive/courses/{course_id}/sages", headers=auth_headers)

        assert resp.status_code == 200
        sages = resp.json()
        sage_ids = [s["id"] for s in sages]
        assert sage1_id in sage_ids
        assert sage2_id in sage_ids


class TestCourseSessionsAPI:
    """测试 /courses/{course_id}/sessions 端点"""

    def test_get_course_sessions_empty(self, client, auth_headers):
        """验证空会话列表返回"""
        world_resp = client.post("/api/archive/worlds", json={"name": "TestWorld3"}, headers=auth_headers)
        world_id = world_resp.json()["id"]

        course_resp = client.post(f"/api/archive/worlds/{world_id}/courses", json={
            "name": "EmptyCourse"
        }, headers=auth_headers)
        course_id = course_resp.json()["id"]

        resp = client.get(f"/api/archive/courses/{course_id}/sessions", headers=auth_headers)

        assert resp.status_code == 200
        sessions = resp.json()
        assert isinstance(sessions, list)

    def test_get_course_sessions_returns_sessions(self, client, auth_headers):
        """验证返回课程关联的会话"""
        # 创建基础数据
        world_resp = client.post("/api/archive/worlds", json={"name": "TestWorld4"}, headers=auth_headers)
        world_id = world_resp.json()["id"]

        course_resp = client.post(f"/api/archive/worlds/{world_id}/courses", json={
            "name": "CourseWithSessions"
        }, headers=auth_headers)
        course_id = course_resp.json()["id"]

        # 启动会话
        start_resp = client.post(f"/api/learning/courses/{course_id}/start", headers=auth_headers)
        assert start_resp.status_code == 200
        session_id = start_resp.json()["session_id"]

        # 获取会话
        resp = client.get(f"/api/archive/courses/{course_id}/sessions", headers=auth_headers)

        assert resp.status_code == 200
        sessions = resp.json()
        assert len(sessions) >= 1
        assert any(s["id"] == session_id for s in sessions)


class TestCourseMemoryFactsAPI:
    """测试 /courses/{course_id}/memory-facts 端点"""

    def test_get_memory_facts_stats_only(self, client, auth_headers, db_session: Session):
        """验证 stats_only=true 返回统计信息"""
        # 创建测试数据
        world_resp = client.post("/api/archive/worlds", json={"name": "TestWorld5"}, headers=auth_headers)
        world_id = world_resp.json()["id"]

        # 创建 Sage 并绑定
        sage_resp = client.post("/api/archive/character", json={
            "name": "MemorySage", "type": "sage"
        }, headers=auth_headers)
        sage_id = sage_resp.json()["id"]

        client.post(f"/api/archive/worlds/{world_id}/characters", json={
            "character_id": sage_id,
            "role": "sage",
            "is_primary": True
        }, headers=auth_headers)

        # 创建记忆
        memory = MemoryFact(
            character_id=sage_id,
            world_id=world_id,
            fact_type="student_state",
            content="Test fact",
            salience=0.8,
        )
        db_session.add(memory)
        db_session.commit()

        # 创建课程
        course_resp = client.post(f"/api/archive/worlds/{world_id}/courses", json={
            "name": "MemoryCourse"
        }, headers=auth_headers)
        course_id = course_resp.json()["id"]

        # 调用 API
        resp = client.get(f"/api/archive/courses/{course_id}/memory-facts", params={"stats_only": "true"}, headers=auth_headers)

        assert resp.status_code == 200
        stats = resp.json()
        assert "total" in stats
        assert "by_type" in stats
        assert "avg_salience" in stats

    def test_get_memory_facts_with_list(self, client, auth_headers, db_session: Session):
        """验证 stats_only=false 返回统计 + 记忆列表"""
        world_resp = client.post("/api/archive/worlds", json={"name": "TestWorld6"}, headers=auth_headers)
        world_id = world_resp.json()["id"]

        sage_resp = client.post("/api/archive/character", json={
            "name": "MemorySage2", "type": "sage"
        }, headers=auth_headers)
        sage_id = sage_resp.json()["id"]

        client.post(f"/api/archive/worlds/{world_id}/characters", json={
            "character_id": sage_id,
            "role": "sage",
            "is_primary": True
        }, headers=auth_headers)

        course_resp = client.post(f"/api/archive/worlds/{world_id}/courses", json={
            "name": "MemoryCourse2"
        }, headers=auth_headers)
        course_id = course_resp.json()["id"]

        # 不带 stats_only
        resp = client.get(f"/api/archive/courses/{course_id}/memory-facts", headers=auth_headers)

        assert resp.status_code == 200
        data = resp.json()
        assert "stats" in data
        assert "facts" in data
        assert isinstance(data["facts"], list)
