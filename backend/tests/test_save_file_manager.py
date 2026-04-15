"""Tests for SaveFileManager — Issue #207 Phase 1"""
import json
import os
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

# We patch SAVE_DIR to use a temp directory
from backend.services.save_file_manager import SaveFileManager


@pytest.fixture()
def tmp_save_dir(tmp_path: Path):
    """Patch SAVE_DIR to use a temporary directory."""
    with patch.object(SaveFileManager, "__module__") as _:
        # Patch the module-level SAVE_DIR
        import backend.services.save_file_manager as sfm
        original = sfm.SAVE_DIR
        sfm.SAVE_DIR = tmp_path / "saves"
        yield sfm.SAVE_DIR
        sfm.SAVE_DIR = original


class TestSaveFileManager:
    def test_write_and_read_save_file(self, tmp_save_dir: Path):
        data = {"version": "2.0", "checkpoint_id": 1, "chat_history": []}
        rel_path = SaveFileManager.write_save_file(user_id=1, checkpoint_id=1, data=data)
        assert rel_path.startswith("1/checkpoint_1_")
        assert rel_path.endswith(".json")

        read_data = SaveFileManager.read_save_file(rel_path)
        assert read_data is not None
        assert read_data["version"] == "2.0"
        assert read_data["checkpoint_id"] == 1

    def test_read_nonexistent_file(self, tmp_save_dir: Path):
        result = SaveFileManager.read_save_file("nonexistent/path.json")
        assert result is None

    def test_delete_save_file(self, tmp_save_dir: Path):
        data = {"test": True}
        rel_path = SaveFileManager.write_save_file(user_id=2, checkpoint_id=5, data=data)
        assert SaveFileManager.delete_save_file(rel_path) is True
        assert SaveFileManager.read_save_file(rel_path) is None

    def test_delete_nonexistent_file(self, tmp_save_dir: Path):
        assert SaveFileManager.delete_save_file("nonexistent.json") is False

    def test_get_file_size(self, tmp_save_dir: Path):
        data = {"version": "2.0", "data": "x" * 100}
        rel_path = SaveFileManager.write_save_file(user_id=1, checkpoint_id=3, data=data)
        size = SaveFileManager.get_file_size(rel_path)
        assert size is not None
        assert size > 0

    def test_get_file_size_nonexistent(self, tmp_save_dir: Path):
        assert SaveFileManager.get_file_size("nonexistent.json") is None

    def test_build_save_data(self):
        data = SaveFileManager.build_save_data(
            checkpoint_id=42,
            session_meta={"session_id": 1},
            relationship={"stage": "friend"},
            chat_history=[{"sender_type": "sage", "content": "hello"}],
        )
        assert data["version"] == "2.0"
        assert data["checkpoint_id"] == 42
        assert data["session_meta"]["session_id"] == 1
        assert data["relationship"]["stage"] == "friend"
        assert len(data["chat_history"]) == 1
        assert "created_at" in data

    def test_build_save_data_defaults(self):
        data = SaveFileManager.build_save_data(checkpoint_id=1)
        assert data["session_meta"] == {}
        assert data["chat_history"] == []
        assert data["memory_snapshot"] == {}

    def test_ensure_save_dir(self, tmp_save_dir: Path):
        import backend.services.save_file_manager as sfm
        user_dir = SaveFileManager.ensure_save_dir(user_id=99)
        assert user_dir.exists()
        assert user_dir.name == "99"

    def test_unicode_content(self, tmp_save_dir: Path):
        data = {"content": "你好世界 🌍", "emoji": "🎮"}
        rel_path = SaveFileManager.write_save_file(user_id=1, checkpoint_id=10, data=data)
        read_data = SaveFileManager.read_save_file(rel_path)
        assert read_data["content"] == "你好世界 🌍"
        assert read_data["emoji"] == "🎮"
