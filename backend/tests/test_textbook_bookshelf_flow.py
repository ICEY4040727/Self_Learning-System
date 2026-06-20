"""Regression tests for textbook / bookshelf sharing flow."""

from pathlib import Path

import pytest

from backend.core.config import get_settings
from backend.models.models import TextbookLibrary


@pytest.fixture
def upload_dir(tmp_path, monkeypatch):
    monkeypatch.setenv("UPLOAD_DIR", str(tmp_path))
    get_settings.cache_clear()
    yield tmp_path
    get_settings.cache_clear()


def _create_world_and_courses(client, auth_headers, names):
    world_resp = client.post("/api/worlds", json={"name": "Textbook World"}, headers=auth_headers)
    assert world_resp.status_code == 200
    world_id = world_resp.json()["id"]

    course_ids = []
    for name in names:
        course_resp = client.post(
            f"/api/worlds/{world_id}/courses",
            json={"name": name},
            headers=auth_headers,
        )
        assert course_resp.status_code == 200
        course_ids.append(course_resp.json()["id"])
    return world_id, course_ids


def test_course_textbook_upload_reports_parse_failure(client, auth_headers, upload_dir):
    _, [course_id] = _create_world_and_courses(client, auth_headers, ["Course A"])

    resp = client.post(
        f"/api/courses/{course_id}/textbooks",
        headers=auth_headers,
        files={"file": ("broken.pdf", b"not a real pdf", "application/pdf")},
    )

    assert resp.status_code == 200
    payload = resp.json()
    assert payload["status"] == "error"
    assert payload["is_usable"] is False
    assert payload["error_message"]


def test_bookshelf_upload_respects_configured_size_limit(client, auth_headers, upload_dir, monkeypatch):
    monkeypatch.setenv("TEXTBOOK_MAX_UPLOAD_SIZE_BYTES", "64")
    get_settings.cache_clear()

    resp = client.post(
        "/api/bookshelf/upload",
        headers=auth_headers,
        files={"file": ("large.txt", b"x" * 65, "text/plain")},
    )

    assert resp.status_code == 413
    assert resp.json()["detail"] == "文件超过 64B 限制"


def test_bookshelf_links_are_shared_and_file_lifetime_is_independent(client, auth_headers, db_session, upload_dir):
    _, [course_a, course_b] = _create_world_and_courses(client, auth_headers, ["Course A", "Course B"])

    upload_resp = client.post(
        "/api/bookshelf/upload",
        headers=auth_headers,
        files={"file": ("shared.txt", "shared text".encode("utf-8"), "text/plain")},
    )
    assert upload_resp.status_code == 200
    library_id = upload_resp.json()["id"]

    library_row = db_session.query(TextbookLibrary).filter(TextbookLibrary.id == library_id).one()
    file_path = Path(library_row.file_path)
    assert file_path.exists()

    first_link = client.post(
        f"/api/courses/batch-link-textbooks?course_id={course_a}",
        json=[library_id],
        headers=auth_headers,
    )
    assert first_link.status_code == 200
    first_payload = first_link.json()
    assert first_payload[0]["textbook_id"] is not None
    textbook_a_id = first_payload[0]["textbook_id"]

    second_link = client.post(
        f"/api/courses/batch-link-textbooks?course_id={course_b}",
        json=[library_id],
        headers=auth_headers,
    )
    assert second_link.status_code == 200
    second_payload = second_link.json()
    assert second_payload[0]["textbook_id"] is not None
    textbook_b_id = second_payload[0]["textbook_id"]

    bookshelf = client.get("/api/bookshelf", headers=auth_headers)
    assert bookshelf.status_code == 200
    linked_item = next(item for item in bookshelf.json() if item["id"] == library_id)
    assert linked_item["linked_course_ids"] == [course_a, course_b]

    delete_bookshelf = client.delete(f"/api/bookshelf/{library_id}", headers=auth_headers)
    assert delete_bookshelf.status_code == 409
    assert file_path.exists()

    delete_course_a = client.delete(
        f"/api/courses/{course_a}/textbooks/{textbook_a_id}",
        headers=auth_headers,
    )
    assert delete_course_a.status_code == 204
    assert file_path.exists()

    bookshelf_after_a = client.get("/api/bookshelf", headers=auth_headers)
    assert bookshelf_after_a.status_code == 200
    linked_after_a = next(item for item in bookshelf_after_a.json() if item["id"] == library_id)
    assert linked_after_a["linked_course_ids"] == [course_b]

    delete_course_b = client.delete(
        f"/api/courses/{course_b}/textbooks/{textbook_b_id}",
        headers=auth_headers,
    )
    assert delete_course_b.status_code == 204
    assert file_path.exists()

    delete_bookshelf_after_unlink = client.delete(f"/api/bookshelf/{library_id}", headers=auth_headers)
    assert delete_bookshelf_after_unlink.status_code == 204
    assert not file_path.exists()
