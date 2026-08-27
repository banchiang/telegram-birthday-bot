"""/add conversation: Name -> Date of birth -> Color -> Category (optional)."""

import re
from datetime import date

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
from colors import GOOGLE_CALENDAR_COLORS

NAME, DOB, COLOR, GROUP = range(4)

DOB_RE = re.compile(r"^(\d{1,2})[-/](\d{1,2})(?:[-/](\d{2,4}))?$")


def parse_dob(text: str):
    """Accepts DD-MM-YYYY, DD-MM, DD/MM/YYYY, DD/MM. Year is optional."""
    m = DOB_RE.match(text.strip())
    if not m:
        return None
    day, month, year = m.groups()
    day, month = int(day), int(month)
    year = int(year) if year else None
    if year is not None and year < 100:
        year += 2000 if year < 30 else 1900
    if not (1 <= month <= 12):
        return None
    try:
        # Use a leap year as a safe stand-in so 29 Feb without a year still validates.
        date(year or 2000, month, day)
    except ValueError:
        return None
    return day, month, year


def color_keyboard():
    buttons = []
    row = []
    for cid, c in GOOGLE_CALENDAR_COLORS.items():
        row.append(InlineKeyboardButton(f"{c['emoji']} {c['name']}", callback_data=f"addcolor:{cid}"))
        if len(row) == 2:
            buttons.append(row)
            row = []
    if row:
        buttons.append(row)
    return InlineKeyboardMarkup(buttons)


def group_keyboard(owner_id):
    groups = db.list_groups(owner_id)
    buttons = [[InlineKeyboardButton("— No category —", callback_data="addgroup:none")]]
    for g in groups:
        buttons.append([InlineKeyboardButton(g["name"], callback_data=f"addgroup:{g['id']}")])
    return InlineKeyboardMarkup(buttons)


async def add_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.type != "private":
        await update.message.reply_text("Please DM me to add a birthday — group chats are only used for /remind links.")
        return ConversationHandler.END
    await update.message.reply_text(
        "Let's add a birthday! 🎂\nWhat's the person's name?\n\n(Send /cancel anytime to stop.)"
    )
    return NAME


async def add_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    name = update.message.text.strip()
    if not name:
        await update.message.reply_text("Please send a valid name.")
        return NAME
    context.user_data["add_name"] = name
    await update.message.reply_text(
        "Got it. Now send their date of birth as DD-MM-YYYY (e.g. 25-12-1990),\n"
        "or DD-MM (e.g. 25-12) if you'd rather not include the year."
    )
    return DOB


async def add_dob(update: Update, context: ContextTypes.DEFAULT_TYPE):
    parsed = parse_dob(update.message.text)
    if not parsed:
        await update.message.reply_text(
            "That doesn't look like a valid date. Please use DD-MM-YYYY or DD-MM, e.g. 25-12-1990 or 25-12."
        )
        return DOB
    day, month, year = parsed
    context.user_data["add_day"] = day
    context.user_data["add_month"] = month
    context.user_data["add_year"] = year
    await update.message.reply_text("Pick a color for this birthday:", reply_markup=color_keyboard())
    return COLOR


async def add_color(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    color_id = int(query.data.split(":")[1])
    context.user_data["add_color"] = color_id
    owner_id = update.effective_user.id
    await query.edit_message_text(f"Color: {GOOGLE_CALENDAR_COLORS[color_id]['emoji']} {GOOGLE_CALENDAR_COLORS[color_id]['name']}")
    await context.bot.send_message(
        chat_id=owner_id,
        text="Assign it to a category? (You can manage categories with /group)",
        reply_markup=group_keyboard(owner_id),
    )
    return GROUP


async def add_group(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    owner_id = update.effective_user.id
    raw = query.data.split(":")[1]
    group_id = None if raw == "none" else int(raw)

    name = context.user_data["add_name"]
    day = context.user_data["add_day"]
    month = context.user_data["add_month"]
    year = context.user_data["add_year"]
    color_id = context.user_data["add_color"]

    bday_id = db.add_birthday(owner_id, name, month, day, year, color_id, group_id)

    group_label = ""
    if group_id:
        g = next((g for g in db.list_groups(owner_id) if g["id"] == group_id), None)
        group_label = f" · category: {g['name']}" if g else ""

    date_label = f"{day:02d}-{month:02d}-{year}" if year else f"{day:02d}-{month:02d}"
    color = GOOGLE_CALENDAR_COLORS[color_id]
    await query.edit_message_text(
        f"✅ Saved {color['emoji']} *{name}* — {date_label}{group_label}\nID: `{bday_id}` (use this with /delete)",
        parse_mode="Markdown",
    )
    context.user_data.clear()
    return ConversationHandler.END


async def add_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()
    await update.message.reply_text("Cancelled.")
    return ConversationHandler.END


add_conversation = ConversationHandler(
    entry_points=[CommandHandler("add", add_start)],
    states={
        NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_name)],
        DOB: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_dob)],
        COLOR: [CallbackQueryHandler(add_color, pattern=r"^addcolor:\d+$")],
        GROUP: [CallbackQueryHandler(add_group, pattern=r"^addgroup:(none|\d+)$")],
    },
    fallbacks=[CommandHandler("cancel", add_cancel)],
)
