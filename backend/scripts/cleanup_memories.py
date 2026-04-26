"""Operational entry point: delete expired MemoryFact rows.

Run manually or hook into your own cron / orchestrator:

    python -m backend.scripts.cleanup_memories

We removed the in-process scheduler in feat/v1.0.3 (see
docs/v1.0.3 Review/memory-system-deep-review.md X-5) so expired-memory
cleanup is now an operations-driven concern, not auto-scheduled.
"""
from __future__ import annotations

import logging
import sys

from backend.db.database import SessionLocal
from backend.services.memory_manager import memory_manager

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("cleanup_memories")


def run() -> int:
    db = SessionLocal()
    try:
        deleted = memory_manager.cleanup_expired(db)
        db.commit()
        logger.info("cleanup_memories: deleted %d expired rows", deleted)
        return deleted
    except Exception:
        logger.exception("cleanup_memories failed")
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    sys.exit(0 if run() >= 0 else 1)
