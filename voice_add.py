"""Voice-note birthday add: send a voice message like "Add Sarah\'s
birthday, March 3rd 1995, make it blue" and this transcribes it (OpenAI
speech-to-text) and extracts the name/date/color (a small OpenAI chat call),
then saves it exactly like /add would -- no button-tapping needed.

Requires OPENAI_API_KEY to be set. If it isn\'t, voice notes get a friendly
message pointing back to /add instead of failing silently.
"""

import asyncio
import json
import logging
import os
import subprocess
import tempfile
from datetime import date

from telegram import Update
from telegram.ext import ContextTypes

import colors
import db

logger = logging.getLogger(__name__)

OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
TRANSCRIBE_MODEL = os.environ.get("OPENAI_TRANSCRIBE_MODEL", "gpt-4o-mini-transcribe")
PARSE_MODEL = os.environ.get("OPENAI_PARSE_MODEL", "gpt-4o-mini")

try:
    import openai
    OPENAI_IMPORT_OK = True
except ImportError:
    OPENAI_IMPORT_OK = False

_client = None


def _get_client():
    global _client
    if _client is None:
        _client = openai.OpenAI(api_key=OPENAI_API_KEY)
    return _client


def _convert_to_mp3(src_path: str, dst_path: str):
    """Telegram voice notes are OGG/Opus; OpenAI\'s transcription API doesn\'t
    accept that format directly, so re-encode to mono 16kHz mp3 via ffmpeg."""
    subprocess.run(
        ["ffmpeg", "-y", "-i", src_path, "-ar", "16000", "-ac", "1", dst_path],
        check=True,
        capture_output=True,
    )


def _transcribe(mp3_path: str) -> str:
    client = _get_client()
    with open(mp3_path, "rb") as f:
        result = client.audio.transcriptions.create(model=TRANSCRIBE_MODEL, file=f)
    return result.text


def _parse_birthday(text: str) -> dict:
    client = _get_client()
    color_names = ", ".join(c["name"] for c in colors.GOOGLE_CALENDAR_COLORS.values())
    today_str = date.today().strftime("%A, %d %B %Y")
    prompt = (
        "Extract birthday details from this transcribed voice message. "
        f"Today\'s date is {today_str}, in case a relative date is mentioned.\n\n"
        f"Message: \"{text}\"\n\n"
        "Respond with ONLY a JSON object with these exact keys:\n"
        '- "person_name": the person\'s name as a string, or null if not stated\n'
        '- "day": day of month as an integer 1-31, or null if not stated\n'
        '- "month": month as an integer 1-12, or null if not stated\n'
        '- "year": birth year as an integer, or null if not stated\n'
        f'- "color_name": if a color is mentioned, the single closest match from this '
        f'exact list: [{color_names}] -- otherwise null\n'
    )
    response = client.chat.completions.create(
        model=PARSE_MODEL,
        messages=[{"role": "user", "content": prompt}],
        response_format={"type": "json_object"},
        temperature=0,
    )
    return json.loads(response.choices[0].message.content)


async def handle_voice_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.type != "private":
        return  # don\'t react to voice notes dropped in a linked reminder group

    if not OPENAI_API_KEY or not OPENAI_IMPORT_OK:
        await update.message.reply_text(
            "Voice add isn\'t set up on this bot yet (needs an OPENAI_API_KEY). "
            "Use /add to enter it by typing instead."
        )
        return

    status_msg = await update.message.reply_text("\U0001F3A4 Listening...")

    with tempfile.TemporaryDirectory() as tmpdir:
        ogg_path = os.path.join(tmpdir, "voice.ogg")
        mp3_path = os.path.join(tmpdir, "voice.mp3")

        tg_file = await update.message.voice.get_file()
        await tg_file.download_to_drive(ogg_path)

        try:
            await asyncio.to_thread(_convert_to_mp3, ogg_path, mp3_path)
        except Exception:
            logger.exception("ffmpeg conversion failed")
            await status_msg.edit_text(
                "Couldn\'t process that voice note (audio conversion failed). Please try /add instead."
            )
            return

        try:
            transcript = await asyncio.to_thread(_transcribe, mp3_path)
        except Exception:
            logger.exception("transcription failed")
            await status_msg.edit_text("Couldn\'t transcribe that voice note. Please try again or use /add.")
            return

        if not transcript or not transcript.strip():
            await status_msg.edit_text("I didn\'t catch any speech in that voice note. Please try again.")
            return

        try:
            parsed = await asyncio.to_thread(_parse_birthday, transcript)
        except Exception:
            logger.exception("parsing failed")
            await status_msg.edit_text(
                f"I heard: \"{transcript.strip()}\"\n\n"
                "But couldn\'t understand the birthday details from it. Try /add instead."
            )
            return

    name = (parsed.get("person_name") or "").strip()
    day = parsed.get("day")
    month = parsed.get("month")
    year = parsed.get("year")
    color_name = parsed.get("color_name")

    problems = []
    if not name:
        problems.append("a name")
    date_ok = False
    if day and month and 1 <= month <= 12:
        try:
            date(year or 2000, month, day)
            date_ok = True
        except (ValueError, TypeError):
            date_ok = False
    if not date_ok:
        problems.append("a valid date")

    if problems:
        await status_msg.edit_text(
            f"I heard: \"{transcript.strip()}\"\n\n"
            f"But couldn\'t pick out {' and '.join(problems)} from that. Try rephrasing, e.g. "
            '"Add Sarah\'s birthday, March 3rd 1995, make it blue" -- or use /add instead.'
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
