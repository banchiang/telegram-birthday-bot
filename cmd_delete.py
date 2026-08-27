"""/delete <id> — remove a birthday by its ID (shown in /view or /add)."""

from telegram import Update
from telegram.ext import ContextTypes

import db
from colors import GOOGLE_CALENDAR_COLORS


async def delete_birthday(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.type != "private":
        await update.message.reply_text("Please DM me to delete a birthday.")
        return
    owner_id = update.effective_user.id

    if not context.args or not context.args[0].isdigit():
        await update.message.reply_text(
            "Usage: /delete <id>\nUse /view to see each birthday's ID (shown as [#id])."
        )
        return

    bday_id = int(context.args[0])
    existing = db.get_birthday(owner_id, bday_id)
    if not existing:
        await update.message.reply_text(f"No birthday with ID {bday_id} found under your account.")
        return

    db.delete_birthday(owner_id, bday_id)
    c = GOOGLE_CALENDAR_COLORS[existing["color_id"]]
    await update.message.reply_text(f"🗑️ Deleted {c['emoji']} {existing['name']} (ID {bday_id}).")
