"""
utils.py
--------
Shared utility helpers used across the bot.
"""

from datetime import datetime


def fmt_time(dt: datetime) -> str:
    """
    Format a datetime object into a 12-hour time string with Arabic AM/PM.

    Example output:  2026-05-31  02:45:30 م
    """
    period = "ص" if dt.hour < 12 else "م"
    return dt.strftime(f"%Y-%m-%d  %I:%M:%S {period}")


def fmt_time_str(dt_value) -> str:
    """
    Accept either a datetime object (from Firestore) or a timestamp string
    (legacy SQLite format) and return a 12-hour Arabic-formatted string.

    Handles:
      - datetime / DatetimeWithNanoseconds objects  ← Firestore
      - 'YYYY-MM-DD HH:MM:SS.ffffff' strings        ← legacy SQLite
      - 'YYYY-MM-DD HH:MM:SS' strings               ← legacy SQLite
    """
    # Firestore returns datetime objects directly
    if isinstance(dt_value, datetime):
        return fmt_time(dt_value)

    # Legacy string format (SQLite) — kept for backwards compatibility
    for fmt in ("%Y-%m-%d %H:%M:%S.%f", "%Y-%m-%d %H:%M:%S"):
        try:
            dt = datetime.strptime(str(dt_value).strip(), fmt)
            return fmt_time(dt)
        except ValueError:
            continue

    return str(dt_value)   # fallback — return as-is
