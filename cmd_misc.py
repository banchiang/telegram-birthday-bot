"""/start and /help."""

from telegram import Update
from telegram.ext import ContextTypes

HELP_TEXT = (
    "🎂 *Birthday Bot*\n\n"
    "*Managing birthdays* (DM me):\n"
    "/add — add a new birthday (name, date, color)\n"
    "/delete <id> — remove a birthday by its ID\n"
    "/view — list all birthdays, soonest first\n"
    "/view <month> — list birthdays in a given month (e.g. /view march)\n"
    "/view group <name> — list birthdays in a category\n\n"
    "*Categories:*\n"
    "/group — see category commands (create/list/assign/delete)\n\n"
    "*Group reminders:*\n"
    "/remind — see how to connect a Telegram group to a category\n\n"
    "*Automatic reminders:*\n"
    "• Every day at 00:00 (Asia/Singapore), I'll DM you if anyone has a birthday today.\n"
    "• On the 1st of each month at 00:00, I'll DM you the full list of birthdays that month.\n"
    "• Any Telegram group linked with /remind also gets a same-day post for its category."
)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Hi! I'm your birthday reminder bot. 🎂\n\n" + HELP_TEXT, parse_mode="Markdown"
    )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(HELP_TEXT, parse_mode="Markdown")
