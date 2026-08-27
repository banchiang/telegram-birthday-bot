"""Shared voice-note utilities: local speech-to-text (faster-whisper, free,
runs on this server, no API key or per-use cost) and a rule-based date
extractor. Used by /add and /edit\'s date-of-birth step, which accepts
either typed text or a voice note saying the date.
"""

import logging
import os
import re
from datetime import date

logger = logging.getLogger(__name__)

WHISPER_MODEL_SIZE = os.environ.get("WHISPER_MODEL_SIZE", "base")

try:
    from faster_whisper import WhisperModel
    FASTER_WHISPER_IMPORT_OK = True
except ImportError:
    FASTER_WHISPER_IMPORT_OK = False

_model = None


def get_model():
    global _model
    if _model is None:
        logger.info("Loading local speech-to-text model (%s)... first run downloads it.", WHISPER_MODEL_SIZE)
        _model = WhisperModel(WHISPER_MODEL_SIZE, device="cpu", compute_type="int8")
    return _model


def transcribe(audio_path: str) -> str:
    """Blocking call -- run this via asyncio.to_thread() from a handler."""
    model = get_model()
    segments, _info = model.transcribe(audio_path, beam_size=5)
    return " ".join(seg.text.strip() for seg in segments).strip()


# ---------------------------------------------------------- date parsing (free, rule-based)

MONTH_NAMES = {
    "january": 1, "jan": 1, "february": 2, "feb": 2, "march": 3, "mar": 3,
    "april": 4, "apr": 4, "may": 5, "june": 6, "jun": 6, "july": 7, "jul": 7,
    "august": 8, "aug": 8, "september": 9, "sept": 9, "sep": 9,
    "october": 10, "oct": 10, "november": 11, "nov": 11, "december": 12, "dec": 12,
}
MONTH_NAME_ALT = "|".join(sorted(MONTH_NAMES.keys(), key=len, reverse=True))
ORDINAL = r"(?:st|nd|rd|th)?"

PAT_MONTH_DAY_YEAR = re.compile(
    rf"\b(?P<month>{MONTH_NAME_ALT})\.?\s+(?P<day>\d{{1,2}}){ORDINAL}\b(?:\s*,?\s*(?P<year>\d{{4}}))?",
    re.IGNORECASE,
)
PAT_DAY_MONTH_YEAR = re.compile(
    rf"\b(?P<day>\d{{1,2}}){ORDINAL}\s+(?:of\s+)?(?P<month>{MONTH_NAME_ALT})\.?\b(?:\s*,?\s*(?P<year>\d{{4}}))?",
    re.IGNORECASE,
)
PAT_NUMERIC = re.compile(r"\b(?P<day>\d{1,2})[-/](?P<month>\d{1,2})(?:[-/](?P<year>\d{2,4}))?\b")


def valid_date(day, month, year):
    try:
        date(year or 2000, month, day)
        return True
    except (ValueError, TypeError):
        return False


def extract_date(text):
    """Search text for a date in common spoken formats (month-name first,
    since that\'s how people actually speak dates; falls back to numeric
    DD-MM[-YYYY], matching the rest of this bot\'s date format).
    Returns (day, month, year_or_None, matched_span_text) or all-None."""
    for pat in (PAT_MONTH_DAY_YEAR, PAT_DAY_MONTH_YEAR):
        m = pat.search(text)
        if m:
            day = int(m.group("day"))
            month = MONTH_NAMES.get(m.group("month").lower())
            year_raw = m.group("year")
            year = int(year_raw) if year_raw else None
            if month and valid_date(day, month, year):
                return day, month, year, m.group(0)
    m = PAT_NUMERIC.search(text)
    if m:
        day = int(m.group("day"))
        month = int(m.group("month"))
        year_raw = m.group("year")
        year = None
        if year_raw:
            year = int(year_raw)
            if year < 100:
                year += 2000 if year < 30 else 1900
        if valid_date(day, month, year):
            return day, month, year, m.group(0)
    return None, None, None, None
