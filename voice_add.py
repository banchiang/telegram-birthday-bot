"""Voice-note birthday add: send a voice message like "Add Sarah\'s
birthday, March 3rd 1995, make it blue" and this transcribes it locally
(faster-whisper -- runs on the bot\'s own server, no API key, no per-use
cost, nothing leaves the machine) and pulls out the name/date/color with a
small rule-based text parser, then saves it exactly like /add would.
"""

import asyncio
import logging
import os
import re
import tempfile
from datetime import date

from telegram import Update
from telegram.ext import ContextTypes

import colors
import db

logger = logging.getLogger(__name__)

WHISPER_MODEL_SIZE = os.environ.get("WHISPER_MODEL_SIZE", "base")

try:
    from faster_whisper import WhisperModel
    FASTER_WHISPER_IMPORT_OK = True
except ImportError:
    FASTER_WHISPER_IMPORT_OK = False

_model = None


def _get_model():
    global _model
    if _model is None:
        logger.info("Loading local speech-to-text model (%s)... first run downloads it.", WHISPER_MODEL_SIZE)
        _model = WhisperModel(WHISPER_MODEL_SIZE, device="cpu", compute_type="int8")
    return _model


def _transcribe(audio_path: str) -> str:
    model = _get_model()
    segments, _info = model.transcribe(audio_path, beam_size=5)
    return " ".join(seg.text.strip() for seg in segments).strip()


# ---------------------------------------------------------- text parsing (free, rule-based)

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


def _valid_date(day, month, year):
    try:
        date(year or 2000, month, day)
        return True
    except (ValueError, TypeError):
        return False


def _extract_date(text):
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
            if month and _valid_date(day, month, year):
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
        if _valid_date(day, month, year):
            return day, month, year, m.group(0)
    return None, None, None, None


COLOR_SYNONYMS = {
    "blue": "Peacock", "green": "Basil", "yellow": "Banana", "purple": "Grape",
    "orange": "Tangerine", "gray": "Graphite", "grey": "Graphite",
    "teal": "Turquoise", "cyan": "Turquoise", "violet": "Grape", "magenta": "Pink",
    "indigo": "Navy",
}


def _extract_color(text):
    """Look for one of the bot\'s 21 color names, or a common everyday color
    word mapped to the closest one. Returns (canonical_name_or_None, matched_span_or_None)."""
    lowered = text.lower()
    names = [c["name"] for c in colors.GOOGLE_CALENDAR_COLORS.values()]
    for name in sorted(names, key=len, reverse=True):
        m = re.search(rf"\b{re.escape(name.lower())}\b", lowered)
        if m:
            return name, text[m.start():m.end()]
    for word, canon in sorted(COLOR_SYNONYMS.items(), key=lambda kv: -len(kv[0])):
        m = re.search(rf"\b{re.escape(word)}\b", lowered)
        if m:
            return canon, text[m.start():m.end()]
    return None, None


FILLER_LEADING = re.compile(r"^\s*(please\s+)?add\s+", re.IGNORECASE)
BIRTHDAY_WORDS = re.compile(r"\b(birthday|born|date of birth|dob)\b", re.IGNORECASE)
POSSESSIVE = re.compile(r"[\u2019\x27]s\b")
CONNECTORS = re.compile(r"\b(for|on|of|in|as)\b", re.IGNORECASE)
RELATION_FILLER = re.compile(
    r"\b(my|our|colleague|coworker|co-worker|friend|sister|brother|mom|mother|dad|father|"
    r"wife|husband|partner|cousin|boss|neighbou?r|roommate|aunt|uncle|grandma|grandpa)\b",
    re.IGNORECASE,
)
MAKE_IT = re.compile(r"\bmake\s+it\b", re.IGNORECASE)
COLOUR_WORD = re.compile(r"\bcolou?r(ed)?\b", re.IGNORECASE)


def _extract_name(original_text, date_span, color_span):
    working = original_text
    if date_span:
        working = working.replace(date_span, " ", 1)
    if color_span:
        working = working.replace(color_span, " ", 1)
    working = FILLER_LEADING.sub("", working)
    working = BIRTHDAY_WORDS.sub("", working)
    working = POSSESSIVE.sub("", working)
    working = CONNECTORS.sub(" ", working)
    working = MAKE_IT.sub(" ", working)
    working = COLOUR_WORD.sub(" ", working)
    working = RELATION_FILLER.sub(" ", working)
    working = re.sub(r"[,.]", " ", working)
    working = re.sub(r"\s+", " ", working).strip()
    return working or None


def parse_birthday_text(text: str) -> dict:
    """Free, rule-based extraction (no external API): pulls a name/date/color
    out of a transcribed sentence with regex. Less flexible than an LLM with
    unusual phrasing, but $0 per use and nothing leaves your server."""
    day, month, year, date_span = _extract_date(text)
    color_name, color_span = _extract_color(text)
    name = _extract_name(text, date_span, color_span)
    return {"person_name": name, "day": day, "month": month, "year": year, "color_name": color_name}


# ------------------------------------------------------------------------- handler

async def handle_voice_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.type != "private":
        return  # don\'t react to voice notes dropped in a linked reminder group

    if not FASTER_WHISPER_IMPORT_OK:
        await update.message.reply_text(
            "Voice add isn\'t available on this deployment (missing the speech-to-text "
            "package). Use /add to enter it by typing instead."
        )
        return

    status_msg = await update.message.reply_text("\U0001F3A4 Listening...")

    with tempfile.TemporaryDirectory() as tmpdir:
        ogg_path = os.path.join(tmpdir, "voice.ogg")
        tg_file = await update.message.voice.get_file()
        await tg_file.download_to_drive(ogg_path)

        try:
            transcript = await asyncio.to_thread(_transcribe, ogg_path)
        except Exception:
            logger.exception("local transcription failed")
            await status_msg.edit_text("Couldn\'t transcribe that voice note. Please try again or use /add.")
            return

    if not transcript or not transcript.strip():
        await status_msg.edit_text("I didn\'t catch any speech in that voice note. Please try again.")
        return

    parsed = parse_birthday_text(transcript)

    name = (parsed.get("person_name") or "").strip()
    day = parsed.get("day")
    month = parsed.get("month")
    year = parsed.get("year")
    color_name = parsed.get("color_name")

    problems = []
    if not name:
        problems.append("a name")
    date_ok = bool(day and month and 1 <= month <= 12 and _valid_date(day, month, year))
    if not date_ok:
        problems.append("a valid date")

    if problems:
        await status_msg.edit_text(
            f"I heard: \"{transcript.strip()}\"\n\n"
            f"But couldn\'t pick out {' and '.join(problems)} from that. Try rephrasing, e.g. "
            '"Add Sarah\'s birthday, March 3rd 1995, make it blue" (day before month, like the rest '
            "of this bot) -- or use /add instead."
        )
        return

    color_id = colors.color_id_by_name(color_name) or 1  # default: Lavender, if no color was said
    owner_id = update.effective_user.id
    bday_id = db.add_birthday(owner_id, name, month, day, year, color_id, None)

    c = colors.GOOGLE_CALENDAR_COLORS[color_id]
    date_label = f"{day:02d}-{month:02d}-{year}" if year else f"{day:02d}-{month:02d}"
    await status_msg.edit_text(
        f"\U0001F3A4 Heard: \"{transcript.strip()}\"\n\n"
        f"\u2705 Saved {c['emoji']} *{name}* \u2014 {date_label}\n"
        f"ID: `{bday_id}` (use /delete {bday_id} if this isn\'t right)",
        parse_mode="Markdown",
    )
