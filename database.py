"""
database.py
-----------
All async SQLite database operations using aiosqlite.
"""

import logging
from datetime import datetime
from typing import Optional

import aiosqlite

from config import DATABASE_PATH

logger = logging.getLogger(__name__)


# ──────────────────────────────────────────────
# Initialization
# ──────────────────────────────────────────────

async def init_db() -> None:
    """Create the students_reports table if it does not exist."""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        await db.execute(
            """
            CREATE TABLE IF NOT EXISTS students_reports (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                telegram_id     INTEGER  NOT NULL,
                full_name       TEXT     NOT NULL,
                college         TEXT     NOT NULL,
                department      TEXT     NOT NULL,
                file_id         TEXT     NOT NULL,
                submission_time TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        await db.commit()
    logger.info("Database initialised at '%s'.", DATABASE_PATH)


# ──────────────────────────────────────────────
# Write Operations
# ──────────────────────────────────────────────

async def save_report(
    telegram_id: int,
    full_name: str,
    college: str,
    department: str,
    file_id: str,
) -> datetime:
    """
    Insert a new student report into the database.

    Returns the submission timestamp so it can be forwarded to the admin.
    """
    submission_time = datetime.now()
    async with aiosqlite.connect(DATABASE_PATH) as db:
        await db.execute(
            """
            INSERT INTO students_reports
                (telegram_id, full_name, college, department, file_id, submission_time)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (telegram_id, full_name, college, department, file_id, submission_time),
        )
        await db.commit()
    logger.info(
        "Saved report: telegram_id=%s | name=%s | college=%s | dept=%s",
        telegram_id, full_name, college, department,
    )
    return submission_time


# ──────────────────────────────────────────────
# Read Operations
# ──────────────────────────────────────────────

async def get_stats() -> dict:
    """
    Return a statistics dict with totals per department and overall total.

    Structure:
        {
            "total": int,
            "by_department": { dept_arabic_name: count, ... }
        }
    """
    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row

        # Total count
        cursor = await db.execute("SELECT COUNT(*) AS total FROM students_reports")
        row = await cursor.fetchone()
        total = row["total"] if row else 0

        # Per-department count
        cursor = await db.execute(
            "SELECT department, COUNT(*) AS cnt FROM students_reports GROUP BY department"
        )
        rows = await cursor.fetchall()

    by_department = {r["department"]: r["cnt"] for r in rows}
    return {"total": total, "by_department": by_department}


async def get_reports_by_department(department_name: str) -> list[dict]:
    """
    Fetch all reports for a given department (Arabic name).

    Returns a list of dicts with keys: full_name, file_id, submission_time.
    """
    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            """
            SELECT full_name, file_id, submission_time
            FROM students_reports
            WHERE department = ?
            ORDER BY submission_time ASC
            """,
            (department_name,),
        )
        rows = await cursor.fetchall()

    return [dict(r) for r in rows]


async def get_all_departments() -> list[str]:
    """Return a distinct list of departments that have at least one submission."""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            "SELECT DISTINCT department FROM students_reports ORDER BY department"
        )
        rows = await cursor.fetchall()
    return [r["department"] for r in rows]


async def get_all_reports() -> list[dict]:
    """
    Fetch every submitted report ordered by submission time (oldest first).

    Returns a list of dicts with keys:
        full_name, college, department, file_id, submission_time
    """
    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            """
            SELECT full_name, college, department, file_id, submission_time
            FROM students_reports
            ORDER BY submission_time ASC
            """
        )
        rows = await cursor.fetchall()
    return [dict(r) for r in rows]


# ──────────────────────────────────────────────
# Superadmin Operations
# ──────────────────────────────────────────────

async def check_existing_submission(telegram_id: int) -> bool:
    """
    Return True if the student has already submitted a report.
    Used to enforce the one-submission-per-student rule.
    """
    async with aiosqlite.connect(DATABASE_PATH) as db:
        cursor = await db.execute(
            "SELECT 1 FROM students_reports WHERE telegram_id = ? LIMIT 1",
            (telegram_id,),
        )
        row = await cursor.fetchone()
    return row is not None


async def get_all_students_brief() -> list[dict]:
    """
    Fetch a brief list of all submitted students for the superadmin deletion panel.

    Returns a list of dicts with keys: id, telegram_id, full_name, college, department.
    """
    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            """
            SELECT id, telegram_id, full_name, college, department
            FROM students_reports
            ORDER BY submission_time ASC
            """
        )
        rows = await cursor.fetchall()
    return [dict(r) for r in rows]


async def get_submission_by_id(submission_id: int) -> Optional[dict]:
    """
    Fetch a single submission row by its primary key.
    Returns None if not found.
    """
    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            """
            SELECT id, telegram_id, full_name, college, department, submission_time
            FROM students_reports
            WHERE id = ?
            """,
            (submission_id,),
        )
        row = await cursor.fetchone()
    return dict(row) if row else None


async def delete_submission_by_id(submission_id: int) -> bool:
    """
    Delete a submission by primary key.
    Returns True if a row was actually deleted, False if the ID did not exist.
    """
    async with aiosqlite.connect(DATABASE_PATH) as db:
        cursor = await db.execute(
            "DELETE FROM students_reports WHERE id = ?",
            (submission_id,),
        )
        await db.commit()
        deleted = cursor.rowcount > 0
    if deleted:
        logger.info("Deleted submission id=%s by superadmin.", submission_id)
    return deleted


async def delete_all_submissions() -> int:
    """
    Delete every row in students_reports.
    Returns the number of rows deleted.
    """
    async with aiosqlite.connect(DATABASE_PATH) as db:
        cursor = await db.execute("DELETE FROM students_reports")
        await db.commit()
        count = cursor.rowcount
    logger.warning("Superadmin deleted ALL %s submissions.", count)
    return count
