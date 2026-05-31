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


def fmt_time_str(dt_str: str) -> str:
    """
    Parse a stored timestamp string and reformat it to 12-hour with Arabic AM/PM.
    Handles both 'YYYY-MM-DD HH:MM:SS' and 'YYYY-MM-DD HH:MM:SS.ffffff' formats.
    Falls back to the original string if parsing fails.
    """
    for fmt in ("%Y-%m-%d %H:%M:%S.%f", "%Y-%m-%d %H:%M:%S"):
        try:
            dt = datetime.strptime(str(dt_str).strip(), fmt)
            return fmt_time(dt)
        except ValueError:
            continue
    return str(dt_str)   # already formatted or unknown format — return as-is
