"""SaveFileManager — 管理存档 JSON 文件的读写

Issue #207: 记忆系统文件化改造 Phase 1
存档内容写入 data/saves/{user_id}/ 目录下的 JSON 文件，
Checkpoint 表仅存储索引（file_path, file_size_bytes）。
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

# 默认存档根目录（相对于项目根目录）
SAVE_DIR = Path("data/saves")

# 单文件大小上限 (10 MB)
MAX_FILE_SIZE_BYTES = 10 * 1024 * 1024


class SaveFileManager:
    """管理存档 JSON 文件的读写、删除操作。"""

    @staticmethod
    def ensure_save_dir(user_id: int) -> Path:
        """确保用户存档目录存在: data/saves/{user_id}/"""
        user_dir = SAVE_DIR / str(user_id)
        user_dir.mkdir(parents=True, exist_ok=True)
        return user_dir

    @staticmethod
    def write_save_file(user_id: int, checkpoint_id: int, data: dict[str, Any]) -> str:
        """写入存档文件，返回相对路径。

        Args:
            user_id: 用户 ID
            checkpoint_id: 存档点 ID
            data: 完整存档数据（将序列化为 JSON）

        Returns:
            相对路径，如 "1/checkpoint_123_20260414100000.json"
        """
        user_dir = SaveFileManager.ensure_save_dir(user_id)
        from datetime import UTC, datetime

        timestamp = datetime.now(UTC).strftime("%Y%m%d%H%M%S")
        filename = f"checkpoint_{checkpoint_id}_{timestamp}.json"
        filepath = user_dir / filename

        content = json.dumps(data, ensure_ascii=False, indent=2)
        filepath.write_text(content, encoding="utf-8")

        file_size = filepath.stat().st_size
        logger.info(
            "Wrote save file: %s (%d bytes)",
            filepath,
            file_size,
        )
        return f"{user_id}/{filename}"

    @staticmethod
    def read_save_file(relative_path: str) -> dict[str, Any] | None:
        """读取存档文件。

        Args:
            relative_path: 相对路径，如 "1/checkpoint_123_20260414100000.json"

        Returns:
            解析后的 JSON 字典，文件不存在时返回 None
        """
        filepath = SAVE_DIR / relative_path
        if not filepath.exists():
            logger.warning("Save file not found: %s", filepath)
            return None
        try:
            return json.loads(filepath.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError) as e:
            logger.error("Failed to read save file %s: %s", filepath, e)
            return None

    @staticmethod
    def delete_save_file(relative_path: str) -> bool:
        """删除存档文件。

        Args:
            relative_path: 相对路径

        Returns:
            True 如果文件被删除，False 如果文件不存在
        """
        filepath = SAVE_DIR / relative_path
        if filepath.exists():
            filepath.unlink()
            logger.info("Deleted save file: %s", filepath)
            return True
        logger.warning("Save file not found for deletion: %s", filepath)
        return False

    @staticmethod
    def get_file_size(relative_path: str) -> int | None:
        """获取存档文件大小（字节）。

        Args:
            relative_path: 相对路径

        Returns:
            文件大小，文件不存在时返回 None
        """
        filepath = SAVE_DIR / relative_path
        if not filepath.exists():
            return None
        return filepath.stat().st_size

    @staticmethod
    def build_save_data(
        checkpoint_id: int,
        session_meta: dict[str, Any] | None = None,
        relationship: dict[str, Any] | None = None,
        chat_history: list[dict[str, Any]] | None = None,
        learner_profile_snapshot: dict[str, Any] | None = None,
        memory_snapshot: dict[str, Any] | None = None,
        progress_snapshot: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """构建标准存档 JSON 数据结构。

        Args:
            checkpoint_id: 存档点 ID
            session_meta: 会话元数据
            relationship: 关系状态
            chat_history: 聊天记录
            learner_profile_snapshot: 学习者档案快照
            memory_snapshot: 记忆事实快照
            progress_snapshot: 进度快照

        Returns:
            完整的存档数据字典
        """
        from datetime import UTC, datetime

        data: dict[str, Any] = {
            "version": "2.0",
            "checkpoint_id": checkpoint_id,
            "created_at": datetime.now(UTC).isoformat(),
            "session_meta": session_meta or {},
            "relationship": relationship or {},
            "chat_history": chat_history or [],
            "learner_profile_snapshot": learner_profile_snapshot or {},
            "memory_snapshot": memory_snapshot or {},
            "progress_snapshot": progress_snapshot or {},
        }
        return data