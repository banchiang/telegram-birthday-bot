"""Shared date-math helpers used by both the /view-family commands and the
scheduled jobs, so "does this birthday fall in this range" logic is defined
once instead of duplicated.
"""

from datetime import date, timedelta


def next_occurrence_delta(today: date, month: int, day: int) -> int:
    """Days from today until the next time this month/day occurs (0 = today)."""
    year = today.year
    try:
        candidate = date(year, month, day)
    except ValueError:
        candidate = date(year, month, 28)  # Feb 29 fallback in non-leap years
    if candidate < today:
        try:
            candidate = date(year + 1, month, day)
        except ValueError:
            candidate = date(year + 1, month, 28)
    return (candidate - today).days


def week_bounds(today: date):
    """Return (monday, sunday) dates for the week containing `today`."""
    monday = today - timedelta(days=today.weekday())
    sunday = monday + timedelta(days=6)
    return monday, sunday


def occurrence_in_range(month: int, day: int, start: date, end: date):
    """If this month/day's next occurrence on/after `start` falls within
    [start, end], return that concrete date; otherwise return None."""
    year = start.year
    try:
        candidate = date(year, month, day)
    except ValueError:
        candidate = date(year, month, 28)
    if candidate < start:
        try:
            candidate = date(year + 1, month, day)
        except ValueError:
            candidate = date(year + 1, month, 28)
    if start <= candidate <= end:
        return candidate
    return None
