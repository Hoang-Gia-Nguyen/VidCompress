import sqlite3
from pathlib import Path
from datetime import datetime, timedelta, timezone

import pytest

from app.jobrepo import (
    EnqueueResult,
    Job,
    SQLiteJobRepository,
)


# ---------- fixtures ----------


@pytest.fixture
def db_path(tmp_path: Path) -> Path:
    return tmp_path / "jobs.db"


@pytest.fixture
def repo(db_path: Path) -> SQLiteJobRepository:
    return SQLiteJobRepository(str(db_path))


@pytest.fixture
def sample_media_path(tmp_path: Path) -> Path:
    p = tmp_path / "dummy.mp4"
    p.write_text("fake media content")
    return p


# ---------- helpers ----------


def get_job_row(db_path: Path, job_id: int) -> sqlite3.Row:
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    try:
        return conn.execute("SELECT * FROM jobs WHERE id = ?", (job_id,)).fetchone()
    finally:
        conn.close()


def set_job_updated_at(db_path: Path, job_id: int, minutes_ago: int):
    """Artificially set a job's updated_at to be in the past for stale testing."""
    conn = sqlite3.connect(str(db_path))
    try:
        past_time = datetime.now(timezone.utc) - timedelta(minutes=minutes_ago)
        conn.execute(
            "UPDATE jobs SET updated_at = ? WHERE id = ?",
            (past_time.strftime("%Y-%m-%d %H:%M:%S"), job_id),
        )
        conn.commit()
    finally:
        conn.close()


# ---------- enqueue ----------


def test_enqueue_new_job(repo: SQLiteJobRepository, sample_media_path: Path):
    result = repo.enqueue(sample_media_path)

    assert result is EnqueueResult.NEW

    job = repo.get_next()
    assert job is not None
    assert job.path == sample_media_path.resolve()


def test_enqueue_same_job_skipped(repo: SQLiteJobRepository, sample_media_path: Path):
    assert repo.enqueue(sample_media_path) is EnqueueResult.NEW
    assert repo.enqueue(sample_media_path) is EnqueueResult.SKIPPED


def test_enqueue_file_changed_reenqueues(
    repo: SQLiteJobRepository, sample_media_path: Path
):
    assert repo.enqueue(sample_media_path) is EnqueueResult.NEW

    # Simulate content change
    sample_media_path.write_text("modified content")
    import os
    import time

    new_mtime = time.time() + 10
    os.utime(sample_media_path, (new_mtime, new_mtime))

    assert repo.enqueue(sample_media_path) is EnqueueResult.NEW


# ---------- get_next / processing ----------


def test_get_next_marks_processing(
    repo: SQLiteJobRepository, sample_media_path: Path, db_path: Path
):
    repo.enqueue(sample_media_path)

    job = repo.get_next()
    assert isinstance(job, Job)

    row = get_job_row(db_path, job.id)
    assert row["status"] == "processing"


def test_get_next_empty(repo: SQLiteJobRepository):
    assert repo.get_next() is None


# ---------- Resume / stale processing jobs ----------


def test_get_next_reclaims_stale_processing_job(
    repo: SQLiteJobRepository, sample_media_path: Path, db_path: Path
):
    """A job stuck in 'processing' state older than the timeout should be reclaimed."""
    repo.enqueue(sample_media_path)
    job = repo.get_next()
    assert job is not None

    # Artificially age the job to be > timeout (default 600s = 10 min)
    # We'll use a repo with a very short timeout to make the test fast
    set_job_updated_at(db_path, job.id, 20)  # 20 minutes ago

    # Create a new repo instance with the same DB but a short timeout
    short_repo = SQLiteJobRepository(str(db_path), retry_timeout=60)  # 1 minute

    # get_next should now reclaim the stale processing job as pending
    reclaimed = short_repo.get_next()
    assert reclaimed is not None
    # The reclaimed job should be the same file
    assert reclaimed.path == sample_media_path.resolve()

    # Verify it was marked as pending then processing
    row = get_job_row(db_path, reclaimed.id)
    assert row["status"] == "processing"
    assert row["error"] == "resumed after timeout"


def test_get_next_does_not_reclaim_fresh_processing_job(
    repo: SQLiteJobRepository, sample_media_path: Path, db_path: Path
):
    """A job in 'processing' state newer than the timeout should NOT be reclaimed."""
    repo.enqueue(sample_media_path)
    job = repo.get_next()
    assert job is not None

    # Job was just created, so it's fresh (less than 1 minute old)
    # Try to reclaim with a 10-minute timeout
    short_repo = SQLiteJobRepository(str(db_path), retry_timeout=600)  # 10 min

    # Since the job is fresh, get_next should return None (no reclaimable or pending jobs)
    # Actually, it will be reclaimed after the job is processed and there are no more pending
    # Let's check: the job is in "processing" state, less than 10 min old -> should NOT be reclaimed
    reclaimed = short_repo.get_next()
    assert reclaimed is None, "Fresh processing job should not be reclaimed"


def test_get_stale_processing_jobs(
    repo: SQLiteJobRepository, sample_media_path: Path, db_path: Path
):
    """get_stale_processing_jobs should return stale jobs based on timeout."""
    repo.enqueue(sample_media_path)
    job = repo.get_next()
    assert job is not None

    # No stale jobs yet (just created)
    stale = repo.get_stale_processing_jobs(600)
    assert len(stale) == 0

    # Age the job
    set_job_updated_at(db_path, job.id, 20)

    # Now it should be stale
    stale = repo.get_stale_processing_jobs(60)
    assert len(stale) == 1
    assert stale[0].id == job.id
    assert stale[0].path == sample_media_path.resolve()


# ---------- status transitions ----------


@pytest.mark.parametrize(
    "method, expected_status",
    [
        ("mark_done", "done"),
        ("mark_skipped", "skipped"),
        ("mark_deleted", "deleted"),
        ("mark_archived", "archived"),
    ],
)
def test_mark_status_updates(
    repo: SQLiteJobRepository,
    sample_media_path: Path,
    db_path: Path,
    method: str,
    expected_status: str,
):
    repo.enqueue(sample_media_path)
    job = repo.get_next()

    getattr(repo, method)(job.id)

    row = get_job_row(db_path, job.id)
    assert row["status"] == expected_status


def test_mark_error_sets_error_and_status(
    repo: SQLiteJobRepository,
    sample_media_path: Path,
    db_path: Path,
):
    repo.enqueue(sample_media_path)
    job = repo.get_next()

    repo.mark_error(job.id, "decode failed")

    row = get_job_row(db_path, job.id)
    assert row["status"] == "error"
    assert row["error"] == "decode failed"


# ---------- iter_pending ----------


def test_iter_pending_yields_all_jobs_in_order(
    repo: SQLiteJobRepository, tmp_path: Path
):
    paths = [tmp_path / f"file_{i}.mp4" for i in range(3)]

    for p in paths:
        p.write_text("content")
        repo.enqueue(p)

    jobs = list(repo.iter_pending())

    assert len(jobs) == 3
    assert [j.path for j in jobs] == [p.resolve() for p in paths]


def test_iter_pending_empty(repo: SQLiteJobRepository):
    jobs = list(repo.iter_pending())
    assert jobs == []


# ---------- trash flow ----------


def test_enqueue_and_iter_trash(repo: SQLiteJobRepository, tmp_path: Path):
    p1 = tmp_path / "trash1.mp4"
    p2 = tmp_path / "trash2.mp4"
    p1.write_text("trash")
    p2.write_text("trash")

    repo.enqueue_trash(p1)
    repo.enqueue_trash(p2)

    jobs = list(repo.iter_trash())

    assert len(jobs) == 2
    assert [j.path for j in jobs] == [p1.resolve(), p2.resolve()]


def test_get_next_trash_marks_processing(
    repo: SQLiteJobRepository, db_path: Path, tmp_path: Path
):
    p = tmp_path / "trash.mp4"
    p.write_text("trash")
    repo.enqueue_trash(p)

    job = repo.get_next_trash()
    assert job is not None

    row = get_job_row(db_path, job.id)
    assert row["status"] == "processing"
