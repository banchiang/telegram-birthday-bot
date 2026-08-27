"""/start and /help."""

from telegram import Update
from telegram.ext import ContextTypes

HELP_TEXT = (
    "\U0001F382 *Birthday Bot*\n\n"
    "*Managing birthdays* (DM me):\n"
    "/add \u2014 add a new birthday (name, date, color \u2014 you can speak the date as a voice note)\n"
    "/edit \u2014 pick a birthday by ID and update its name/date/color\n"
    "/delete <id> \u2014 remove a birthday by its ID\n"
    "/week \u2014 birthdays this week\n"
    "/month \u2014 birthdays this month\n"
    "/all \u2014 every birthday, soonest first\n"
    "/view group <name> \u2014 birthdays in one category\n\n"
    "*Categories:*\n"
    "/group \u2014 see category commands (create/list/assign/delete)\n\n"
    "*Group reminders:*\n"
    "/remind \u2014 see how to connect a Telegram group to a category\n\n"
    "*Automatic reminders:*\n"
    "\u2022 Every day at 00:00 (Asia/Singapore), I\'ll DM you if anyone has a birthday today.\n"
    "\u2022 Every Monday at 00:00, I\'ll DM you that week\'s birthdays.\n"
    "\u2022 On the 1st of each month at 00:00, I\'ll DM you the full list of birthdays that month.\n"
    "\u2022 Any Telegram group linked with /remind also gets a same-day post for its category."
)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Hi! I\'m your birthday reminder bot. \U0001F382\n\n" + HELP_TEXT, parse_mode="Markdown"
    )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(HELP_TEXT, parse_mode="Markdown")
