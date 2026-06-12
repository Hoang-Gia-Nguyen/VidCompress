import sqlite3
from abc import ABC, abstractmethod
from contextlib import contextmanager
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Iterator, Optional

from app.logger import logger


class EnqueueResult(Enum):
    NEW = "new"
    SKIPPED = "skipped"
    RETRY = "retry"


@dataclass
class Job:
    id: int
    path: Path


class JobRepository(ABC):
    """
    Abstract base class for job repositories.

    A job repository is responsible for managing jobs, including enqueuing new jobs,
    retrieving the next job to process, and updating the status of jobs.

    Subclasses must implement the abstract methods defined in this class.
    """

    @abstractmethod
    def enqueue(self, path: Path) -> EnqueueResult:
        """
        Enqueue a new job.

        Args:
            path (Path): The path of the job to enqueue.

        Returns:
            EnqueueResult: The result of enqueuing the job.
        """
        pass

    @abstractmethod
    def get_next(self) -> Optional[Job]:
        """
        Get the next job to process.

        Returns:
            Optional[Job]: The next job to process, or None if there are no jobs.
        """
        pass

    @abstractmethod
    def mark_done(self, job_id: int) -> None:
        """
        Mark a job as done.

        Args:
            job_id (int): The ID of the job to mark as done.
        """
        pass

    @abstractmethod
    def mark_error(self, job_id: int, error: str) -> None:
        """
        Mark a job as having an error.

        Args:
            job_id (int): The ID of the job to mark as having an error.
            error (str): The error message.
        """
        pass

    @abstractmethod
    def mark_skipped(self, job_id: int) -> None:
        """
        Mark a job as skipped.

        Args:
            job_id (int): The ID of the job to mark as skipped.
        """
        pass

    @abstractmethod
    def iter_pending(self) -> Iterator[Job]:
        """
        Iterate over pending jobs.

        Yields:
            Iterator[Job]: An iterator over pending jobs.
        """
        pass

    @abstractmethod
    def mark_deleted(self, job_id: int) -> None:
        """
        Mark a job as deleted.

        Args:
            job_id (int): The ID of the job to mark as deleted.
        """
        pass

    @abstractmethod
    def mark_archived(self, job_id: int) -> None:
        """
        Mark a job as archived.

        Args:
            job_id (int): The ID of the job to mark as archived.
        """
        pass

    @abstractmethod
    def get_next_trash(self) -> Optional[Job]:
        """
        Get the next job to process from the trash.

        Returns:
            Optional[Job]: The next job to process from the trash, or None if there are no jobs.
        """
        pass

    @abstractmethod
    def iter_trash(self) -> Iterator[Job]:
        """
        Iterate over jobs in the trash.

        Yields:
            Iterator[Job]: An iterator over jobs in the trash.
        """
        pass

    @abstractmethod
    def get_stale_processing_jobs(self, timeout_seconds: int) -> list[Job]:
        """
        Get jobs stuck in 'processing' state longer than the given timeout.

        Args:
            timeout_seconds (int): Number of seconds after which a processing job is considered stale.

        Returns:
            list[Job]: Stale processing jobs.
        """
        pass


class SQLiteJobRepository(JobRepository):
    def __init__(self, db_path: str, retry_timeout: int = 600):
        self.db_path = db_path
        self.retry_timeout = retry_timeout
        self._init_db()

    def _init_db(self):
        with self._conn() as conn:
            conn.executescript(
                """
            CREATE TABLE IF NOT EXISTS jobs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                path TEXT UNIQUE,
                size INTEGER,
                mtime REAL,
                status TEXT NOT NULL,
                error TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
            );

            CREATE INDEX IF NOT EXISTS idx_jobs_status
            ON jobs(status);
            """
            )

    @contextmanager
    def _conn(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        finally:
            conn.close()

    def enqueue(self, path: Path) -> EnqueueResult:
        path = path.resolve()
        path_str = str(path)

        stat = path.stat()
        current_size = stat.st_size
        current_mtime = stat.st_mtime

        with self._conn() as conn:
            cur = conn.execute(
                "SELECT status, size, mtime FROM jobs WHERE path = ?",
                (path_str,),
            )
            row = cur.fetchone()

            # Case 1: job chưa tồn tại
            if row is None:
                conn.execute(
                    """
                    INSERT INTO jobs (path, size, mtime, status)
                    VALUES (?, ?, ?, 'pending')
                    """,
                    (path_str, current_size, current_mtime),
                )
                return EnqueueResult.NEW

            status, saved_size, saved_mtime = row["status"], row["size"], row["mtime"]

            # Case 2: file changed (size or mtime differ) -> re-enqueue
            if saved_size != current_size or saved_mtime != current_mtime:
                conn.execute(
                    """
                    UPDATE jobs
                    SET status = 'pending',
                        size = ?,
                        mtime = ?,
                        error = NULL,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE path = ?
                    """,
                    (current_size, current_mtime, path_str),
                )
                return EnqueueResult.NEW

            # Case 3: retry job failed
            if status == "error" or status == "failed":
                conn.execute(
                    """
                    UPDATE jobs
                    SET status = 'pending',
                        updated_at = CURRENT_TIMESTAMP
                    WHERE path = ?
                    """,
                    (path_str,),
                )
                return EnqueueResult.RETRY

            # Case 4: pending / processing / done
            return EnqueueResult.SKIPPED

    def enqueue_trash(self, path: Path) -> EnqueueResult:
        path = path.resolve()
        path_str = str(path)

        with self._conn() as conn:
            conn.execute(
                """
                INSERT INTO jobs (path, status)
                VALUES (?, 'trash')
                """,
                (path_str,),
            )
            return EnqueueResult.NEW

    def get_next(self) -> Optional[Job]:
        with self._conn() as conn:
            # First, try to reclaim stale processing jobs
            stale_jobs = self._find_stale_processing_jobs(conn)
            if stale_jobs:
                for j in stale_jobs:
                    logger.info(
                        f"[Resume] Reclaiming job #{j['id']} ({Path(j['path']).name}) "
                        f"stuck in 'processing' state"
                    )
                    conn.execute(
                        """
                        UPDATE jobs
                        SET status = 'pending',
                            error = 'resumed after timeout',
                            updated_at = CURRENT_TIMESTAMP
                        WHERE id = ?
                        """,
                        (j["id"],),
                    )

            # Now get the next pending job
            row = conn.execute(
                """
                SELECT id, path
                FROM jobs
                WHERE status = 'pending'
                ORDER BY id
                LIMIT 1
            """
            ).fetchone()

            if row is None:
                return None

            conn.execute(
                """
                UPDATE jobs
                SET status = 'processing',
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            """,
                (row["id"],),
            )

            return Job(id=row["id"], path=Path(row["path"]))

    def _find_stale_processing_jobs(self, conn) -> list:
        """
        Find jobs stuck in 'processing' state beyond the retry timeout.
        Uses SQLite's datetime functions for comparison.
        """
        timeout_seconds = self.retry_timeout
        rows = conn.execute(
            """
            SELECT id, path
            FROM jobs
            WHERE status = 'processing'
              AND (julianday('now') - julianday(updated_at)) * 86400 > ?
            ORDER BY id
            """,
            (timeout_seconds,),
        ).fetchall()
        return rows

    def get_stale_processing_jobs(self, timeout_seconds: int) -> list[Job]:
        with self._conn() as conn:
            rows = conn.execute(
                """
                SELECT id, path
                FROM jobs
                WHERE status = 'processing'
                  AND (julianday('now') - julianday(updated_at)) * 86400 > ?
                ORDER BY id
                """,
                (timeout_seconds,),
            ).fetchall()
            return [Job(id=r["id"], path=Path(r["path"])) for r in rows]

    def get_next_trash(self) -> Optional[Job]:
        with self._conn() as conn:
            row = conn.execute(
                """
                SELECT id, path
                FROM jobs
                WHERE status = 'trash'
                ORDER BY id
                LIMIT 1
            """
            ).fetchone()

            if row is None:
                return None

            conn.execute(
                """
                UPDATE jobs
                SET status = 'processing',
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            """,
                (row["id"],),
            )

            return Job(id=row["id"], path=Path(row["path"]))

    def mark_done(self, job_id: int) -> None:
        logger.debug(f"[SQLiteJobRepository] Mark done for id {job_id}")
        with self._conn() as conn:
            conn.execute(
                """
                UPDATE jobs
                SET status = 'done',
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            """,
                (job_id,),
            )

    def mark_skipped(self, job_id: int) -> None:
        logger.debug(f"[SQLiteJobRepository] Mark skipped for id {job_id}")
        with self._conn() as conn:
            conn.execute(
                """
                UPDATE jobs
                SET status = 'skipped',
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            """,
                (job_id,),
            )

    def mark_deleted(self, job_id: int) -> None:
        logger.debug(f"[SQLiteJobRepository] Mark deleted for id {job_id}")
        with self._conn() as conn:
            conn.execute(
                """
                UPDATE jobs
                SET status = 'deleted',
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            """,
                (job_id,),
            )

    def mark_archived(self, job_id: int) -> None:
        logger.debug(f"[SQLiteJobRepository] Mark archived for id {job_id}")
        with self._conn() as conn:
            conn.execute(
                """
                UPDATE jobs
                SET status = 'archived',
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            """,
                (job_id,),
            )

    def mark_error(self, job_id: int, error: str) -> None:
        logger.debug(f"[SQLiteJobRepository] Mark error for id {job_id}")
        with self._conn() as conn:
            conn.execute(
                """
                UPDATE jobs
                SET status = 'error',
                    error = ?,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            """,
                (error, job_id),
            )

    def iter_pending(self) -> Iterator[Job]:
        while True:
            job = self.get_next()
            if job is None:
                return
            yield job

    def iter_trash(self) -> Iterator[Job]:
        while True:
            job = self.get_next_trash()
            if job is None:
                return
            yield job
