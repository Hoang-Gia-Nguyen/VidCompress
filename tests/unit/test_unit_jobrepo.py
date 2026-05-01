import sqlite3
from pathlib import Path

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
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    try:
        return conn.execute("SELECT * FROM jobs WHERE id = ?", (job_id,)).fetchone()
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


def test_enqueue_file_changed_reenqueues(repo: SQLiteJobRepository, sample_media_path: Path):
    assert repo.enqueue(sample_media_path) is EnqueueResult.NEW
    
    # Simulate content change
    sample_media_path.write_text("modified content")
    # Also ensure mtime changes (some systems might have low mtime precision)
    import os
    import time
    new_mtime = time.time() + 10
    os.utime(sample_media_path, (new_mtime, new_mtime))

    assert repo.enqueue(sample_media_path) is EnqueueResult.NEW


# def test_enqueue_retry_failed_job(repo: SQLiteJobRepository, sample_media_path: Path):
#     repo.enqueue(sample_media_path)
#     job = repo.get_next()
#     repo.mark_error(job.id, "boom")

#     result = repo.enqueue(sample_media_path)

#     assert result is EnqueueResult.RETRY

#     retry_job = repo.get_next()
#     assert retry_job is not None
#     assert retry_job.id == job.id


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


def test_iter_pending_yields_all_jobs_in_order(repo: SQLiteJobRepository, tmp_path: Path):
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


def test_get_next_trash_marks_processing(repo: SQLiteJobRepository, db_path: Path, tmp_path: Path):
    p = tmp_path / "trash.mp4"
    p.write_text("trash")
    repo.enqueue_trash(p)

    job = repo.get_next_trash()
    assert job is not None

    row = get_job_row(db_path, job.id)
    assert row["status"] == "processing"
