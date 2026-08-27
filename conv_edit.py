"""/edit conversation: pick a birthday by ID, then re-enter its
Name -> Date of birth (text or voice) -> Color, same prompting style as
/add, overwriting that record in place. Category is left untouched (use
/group assign for that).
"""

import asyncio
import calendar
import os
import tempfile

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (
    CommandHandler,
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    CallbackQueryHandler,
    filters,
)

import db
import voice_add
from colors import GOOGLE_CALENDAR_COLORS
from conv_add import parse_dob, capitalize_name

SELECT_ID, NAME, DOB, COLOR = range(4)


def _list_line(b):
    c = GOOGLE_CALENDAR_COLORS[b["color_id"]]
    date_str = f"{b['day']:02d} {calendar.month_abbr[b['month']]}"
    group_str = f" \u00b7 _{b['group_name']}_" if b.get("group_name") else ""
    return f"{c['emoji']} *{date_str}* \u2014 {b['name']}{group_str} [#{b['id']}]"


def color_keyboard():
    buttons = []
    row = []
    for cid, c in GOOGLE_CALENDAR_COLORS.items():
        row.append(InlineKeyboardButton(f"{c['emoji']} {c['name']}", callback_data=f"editcolor:{cid}"))
        if len(row) == 3:
            buttons.append(row)
            row = []
    if row:
        buttons.append(row)
    return InlineKeyboardMarkup(buttons)


async def edit_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.type != "private":
        await update.message.reply_text("Please DM me to edit a birthday.")
        return ConversationHandler.END

    owner_id = update.effective_user.id
    rows = db.list_birthdays(owner_id)
    if not rows:
        await update.message.reply_text("You don\'t have any birthdays yet. Add one with /add.")
        return ConversationHandler.END

    rows.sort(key=lambda b: (b["month"], b["day"]))
    lines = ["\u270F\uFE0F *Which birthday do you want to edit?*", ""] + [_list_line(b) for b in rows]
    lines.append("\nSend the ID (the number after #) of the one to edit. (/cancel to stop)")
    await update.message.reply_text("\n".join(lines), parse_mode="Markdown")
    return SELECT_ID


async def edit_select_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    owner_id = update.effective_user.id
    text = update.message.text.strip().lstrip("#")
    if not text.isdigit():
        await update.message.reply_text("Please send just the ID number, e.g. 3.")
        return SELECT_ID

    bday_id = int(text)
    b = db.get_birthday(owner_id, bday_id)
    if not b:
        await update.message.reply_text(f"No birthday with ID {bday_id} found under your account. Try again.")
        return SELECT_ID

    context.user_data["edit_id"] = bday_id
    date_label = f"{b['day']:02d}-{b['month']:02d}-{b['year']}" if b["year"] else f"{b['day']:02d}-{b['month']:02d}"
    c = GOOGLE_CALENDAR_COLORS[b["color_id"]]
    await update.message.reply_text(
        f"Editing {c['emoji']} *{b['name']}* \u2014 {date_label}.\n\n"
        "What\'s the new name? (send /cancel to stop)",
        parse_mode="Markdown",
    )
    return NAME


async def edit_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    name = update.message.text.strip()
    if not name:
        await update.message.reply_text("Please send a valid name.")
        return NAME
    name = capitalize_name(name)
    context.user_data["edit_name"] = name
    await update.message.reply_text(
        "Got it. Now send the new date of birth as DD-MM-YYYY (e.g. 25-12-1990),\n"
        "or DD-MM (e.g. 25-12) if you\'d rather not include the year.\n\n"
        "\U0001F3A4 Or just send a voice note saying the date."
    )
    return DOB


async def edit_dob(update: Update, context: ContextTypes.DEFAULT_TYPE):
    parsed = parse_dob(update.message.text)
    if not parsed:
        await update.message.reply_text(
            "That doesn\'t look like a valid date. Please use DD-MM-YYYY or DD-MM, e.g. 25-12-1990 or 25-12 "
            "\u2014 or send a voice note saying the date instead."
        )
        return DOB
    day, month, year = parsed
    context.user_data["edit_day"] = day
    context.user_data["edit_month"] = month
    context.user_data["edit_year"] = year
    await update.message.reply_text("Pick a color for this birthday:", reply_markup=color_keyboard())
    return COLOR


async def edit_dob_voice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not voice_add.FASTER_WHISPER_IMPORT_OK:
        await update.message.reply_text(
            "Voice input isn\'t available on this deployment. Please type the date instead, "
            "e.g. 25-12-1990 or 25-12."
        )
        return DOB

    status_msg = await update.message.reply_text("\U0001F3A4 Listening...")

    with tempfile.TemporaryDirectory() as tmpdir:
        ogg_path = os.path.join(tmpdir, "voice.ogg")
        tg_file = await update.message.voice.get_file()
        await tg_file.download_to_drive(ogg_path)
        try:
            transcript = await asyncio.to_thread(voice_add.transcribe, ogg_path)
        except Exception:
            await status_msg.edit_text(
                "Couldn\'t transcribe that. Please try again, or type the date instead, e.g. 25-12-1990 or 25-12."
            )
            return DOB

    if not transcript or not transcript.strip():
        await status_msg.edit_text("I didn\'t catch any speech there. Please try again, or type the date instead.")
        return DOB

    day, month, year, _span = voice_add.extract_date(transcript)
    if day is None:
        await status_msg.edit_text(
            f"I heard: \"{transcript.strip()}\"\n\n"
            "But couldn\'t find a valid date in that. Try again, or type it instead, e.g. 25-12-1990 or 25-12."
        )
        return DOB

    context.user_data["edit_day"] = day
    context.user_data["edit_month"] = month
    context.user_data["edit_year"] = year
    date_label = f"{day:02d}-{month:02d}-{year}" if year else f"{day:02d}-{month:02d}"
    await status_msg.edit_text(f"\U0001F3A4 Heard: \"{transcript.strip()}\" \u2192 {date_label}")
    await context.bot.send_message(
        chat_id=update.effective_user.id, text="Pick a color for this birthday:", reply_markup=color_keyboard()
    )
    return COLOR


async def edit_color(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    owner_id = update.effective_user.id
    color_id = int(query.data.split(":")[1])

    bday_id = context.user_data["edit_id"]
    name = context.user_data["edit_name"]
    day = context.user_data["edit_day"]
    month = context.user_data["edit_month"]
    year = context.user_data["edit_year"]

    ok = db.update_birthday(owner_id, bday_id, name, month, day, year, color_id)

    if not ok:
        await query.edit_message_text("Couldn\'t save that edit \u2014 the record may have been deleted. Check /all.")
        context.user_data.clear()
        return ConversationHandler.END

    c = GOOGLE_CALENDAR_COLORS[color_id]
    date_label = f"{day:02d}-{month:02d}-{year}" if year else f"{day:02d}-{month:02d}"
    await query.edit_message_text(
        f"\u2705 Updated {c['emoji']} *{name}* \u2014 {date_label}\nID: `{bday_id}`",
        parse_mode="Markdown",
    )
    context.user_data.clear()
    return ConversationHandler.END


async def edit_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()
    await update.message.reply_text("Cancelled.")
    return ConversationHandler.END


edit_conversation = ConversationHandler(
    entry_points=[CommandHandler("edit", edit_start)],
    states={
        SELECT_ID: [MessageHandler(filters.TEXT & ~filters.COMMAND, edit_select_id)],
        NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, edit_name)],
        DOB: [
            MessageHandler(filters.TEXT & ~filters.COMMAND, edit_dob),
            MessageHandler(filters.VOICE, edit_dob_voice),
        ],
        COLOR: [CallbackQueryHandler(edit_color, pattern=r"^editcolor:\d+$")],
    },
    fallbacks=[CommandHandler("cancel", edit_cancel)],
)
