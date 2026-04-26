"""Tests for backend.services.scheduler."""

from backend.services import scheduler


def test_build_scheduler_registers_evolve_salience_job():
    """The scheduler must wire up the daily evolve_salience job."""
    sch = scheduler.build_scheduler()
    job_ids = {j.id for j in sch.get_jobs()}
    assert "evolve_salience_daily" in job_ids


def test_evolve_salience_job_runs_against_empty_db(db_session):
    """The job body must not raise when there are no facts to update."""
    # _evolve_salience_job opens its own SessionLocal; the conftest's in-memory
    # engine creates the schema, so a no-op pass is the expected path.
    scheduler._evolve_salience_job()
