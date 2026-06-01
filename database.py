"""
database.py
-----------
All async Firestore database operations using firebase-admin.

Collection : students_reports
Document ID: str(telegram_id)   ← one document per student (enforces the
                                    one-submission rule at the storage level)

Document fields
---------------
telegram_id     : int
full_name       : str
college         : str
department      : str
file_id         : str   (Telegram file_id of the Word document)
submission_time : datetime
"""

import json
import logging
from datetime import datetime
from typing import Optional

import firebase_admin
from firebase_admin import credentials, firestore_async

from config import FIREBASE_CREDENTIALS, FIREBASE_CREDENTIALS_PATH

logger = logging.getLogger(__name__)

# ──────────────────────────────────────────────
# Firebase Initialisation  (runs once at import)
# ──────────────────────────────────────────────

def _init_firebase() -> None:
    """Initialise the Firebase Admin SDK exactly once."""
    if firebase_admin._apps:
        return  # Already initialised

    if FIREBASE_CREDENTIALS:
        # Cloud deployment: full JSON stored in environment variable
        cred = credentials.Certificate(json.loads(FIREBASE_CREDENTIALS))
        logger.info("Firebase: using credentials from FIREBASE_CREDENTIALS env var.")
    else:
        # Local development: JSON file on disk
        cred = credentials.Certificate(FIREBASE_CREDENTIALS_PATH)
        logger.info("Firebase: using credentials from file '%s'.", FIREBASE_CREDENTIALS_PATH)

    firebase_admin.initialize_app(cred)
    logger.info("Firebase Admin SDK initialised successfully.")


_init_firebase()
_db = firestore_async.client()          # Async Firestore client
COLLECTION = "students_reports"         # Firestore collection name


# ──────────────────────────────────────────────
# Initialisation
# ──────────────────────────────────────────────

async def init_db() -> None:
    """
    No-op for Firestore — collections are created automatically on first write.
    Kept for API compatibility with the rest of the codebase.
    """
    logger.info("Firestore ready. Collection: '%s'", COLLECTION)


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
    Save (or overwrite) a student's report.
    Uses telegram_id as the document ID so there is exactly one document
    per student, which naturally enforces the one-submission rule.

    Returns the submission timestamp.
    """
    submission_time = datetime.now()
    doc_ref = _db.collection(COLLECTION).document(str(telegram_id))
    await doc_ref.set({
        "telegram_id":     telegram_id,
        "full_name":       full_name,
        "college":         college,
        "department":      department,
        "file_id":         file_id,
        "submission_time": submission_time,
    })
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
    Return a statistics dict:
        {
            "total": int,
            "by_department": { dept_arabic_name: count, ... }
        }
    """
    by_department: dict[str, int] = {}
    total = 0

    async for doc in _db.collection(COLLECTION).stream():
        data = doc.to_dict()
        total += 1
        dept = data.get("department", "غير محدد")
        by_department[dept] = by_department.get(dept, 0) + 1

    return {"total": total, "by_department": by_department}


async def get_reports_by_department(department_name: str) -> list[dict]:
    """
    Fetch all reports for a given department (Arabic name).
    Returns a list of dicts with keys: full_name, file_id, submission_time.
    """
    query = (
        _db.collection(COLLECTION)
        .where("department", "==", department_name)
    )
    results = []
    async for doc in query.stream():
        data = doc.to_dict()
        results.append({
            "full_name":       data["full_name"],
            "file_id":         data["file_id"],
            "submission_time": data["submission_time"],
        })
    # Sort client-side by submission time (avoids requiring a Firestore composite index)
    results.sort(key=lambda r: r["submission_time"])
    return results


async def get_all_departments() -> list[str]:
    """Return a distinct sorted list of departments that have at least one submission."""
    depts: set[str] = set()
    async for doc in _db.collection(COLLECTION).stream():
        data = doc.to_dict()
        dept = data.get("department")
        if dept:
            depts.add(dept)
    return sorted(depts)


async def get_all_reports() -> list[dict]:
    """
    Fetch every submitted report ordered by submission time (oldest first).
    Returns dicts with keys: full_name, college, department, file_id, submission_time.
    """
    results = []
    async for doc in _db.collection(COLLECTION).stream():
        data = doc.to_dict()
        results.append({
            "full_name":       data["full_name"],
            "college":         data["college"],
            "department":      data["department"],
            "file_id":         data["file_id"],
            "submission_time": data["submission_time"],
        })
    results.sort(key=lambda r: r["submission_time"])
    return results


# ──────────────────────────────────────────────
# Superadmin Operations
# ──────────────────────────────────────────────

async def check_existing_submission(telegram_id: int) -> bool:
    """
    Return True if the student has already submitted a report.
    Because telegram_id is the document ID, this is a single fast lookup.
    """
    doc = await _db.collection(COLLECTION).document(str(telegram_id)).get()
    return doc.exists


async def get_all_students_brief() -> list[dict]:
    """
    Fetch a brief list of all submitted students for the superadmin panel.
    Returns dicts with keys: id, telegram_id, full_name, college, department.
    The 'id' field equals telegram_id and is used as the superadmin action key.
    """
    results = []
    async for doc in _db.collection(COLLECTION).stream():
        data = doc.to_dict()
        results.append({
            "id":          data["telegram_id"],   # used in callback_data
            "telegram_id": data["telegram_id"],
            "full_name":   data["full_name"],
            "college":     data["college"],
            "department":  data["department"],
        })
    results.sort(key=lambda r: r["full_name"])
    return results


async def get_submission_by_id(submission_id: int) -> Optional[dict]:
    """
    Fetch a single submission by its 'id' (= telegram_id).
    Returns None if not found.
    """
    doc = await _db.collection(COLLECTION).document(str(submission_id)).get()
    if not doc.exists:
        return None
    data = doc.to_dict()
    return {
        "id":              data["telegram_id"],
        "telegram_id":     data["telegram_id"],
        "full_name":       data["full_name"],
        "college":         data["college"],
        "department":      data["department"],
        "submission_time": data["submission_time"],
    }


async def delete_submission_by_id(submission_id: int) -> bool:
    """
    Delete a submission by its 'id' (= telegram_id).
    Returns True if a document was actually deleted, False if it didn't exist.
    """
    doc_ref = _db.collection(COLLECTION).document(str(submission_id))
    doc = await doc_ref.get()
    if not doc.exists:
        return False
    await doc_ref.delete()
    logger.info("Deleted submission for telegram_id=%s.", submission_id)
    return True


async def delete_all_submissions() -> int:
    """
    Delete every document in the students_reports collection.
    Returns the number of documents deleted.
    """
    refs = []
    async for doc in _db.collection(COLLECTION).stream():
        refs.append(doc.reference)

    for ref in refs:
        await ref.delete()

    count = len(refs)
    logger.warning("Superadmin deleted ALL %s submissions.", count)
    return count
