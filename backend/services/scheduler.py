"""Background task scheduler.

Owns recurring jobs that must not run on the request hot path. Currently:
  - evolve_salience: daily memory salience decay across all characters.

Single-process model (AsyncIOScheduler in the FastAPI event loop). For
multi-worker deployments, move these jobs to an external cron / dedicated
worker so they don't run N times in parallel.
"""
from __future__ import annotations

import logging

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from backend.db.database import SessionLocal

logger = logging.getLogger(__name__)

_scheduler: AsyncIOScheduler | None = None


def _evolve_salience_job() -> None:
    from backend.services.memory_facts import memory_facts_service

    db = SessionLocal()
    try:
        updated = memory_facts_service.evolve_salience(db)
        db.commit()
        logger.info("scheduled evolve_salience: updated %d facts", updated)
    except Exception:
        logger.exception("scheduled evolve_salience failed")
        db.rollback()
    finally:
        db.close()


def build_scheduler() -> AsyncIOScheduler:
    """Construct the scheduler and register jobs without starting it.

    Separated from start_scheduler so tests can verify job wiring without
    needing a running asyncio event loop.
    """
    sch = AsyncIOScheduler(timezone="UTC")
    sch.add_job(
        _evolve_salience_job,
        trigger=CronTrigger(hour=3, minute=0),
        id="evolve_salience_daily",
        replace_existing=True,
        max_instances=1,
        coalesce=True,
    )
    return sch


def start_scheduler() -> AsyncIOScheduler:
    """Start the global scheduler. Idempotent. Requires a running event loop."""
    global _scheduler
    if _scheduler is not None:
        return _scheduler

    _scheduler = build_scheduler()
    _scheduler.start()
    logger.info(
        "scheduler started; jobs=%s", [j.id for j in _scheduler.get_jobs()]
    )
    return _scheduler


def shutdown_scheduler() -> None:
    """Stop the scheduler if running. Idempotent."""
    global _scheduler
    if _scheduler is None:
        return
    _scheduler.shutdown(wait=False)
    _scheduler = None
    logger.info("scheduler shut down")
