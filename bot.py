"""Entry point: wires up all handlers and the scheduled jobs, then runs
the bot with long-polling.
"""

import logging
import os
from datetime import time
from zoneinfo import ZoneInfo

from telegram import BotCommand, Update
from telegram.ext import Application, ApplicationBuilder, CommandHandler

import db
from cmd_delete import delete_birthday
from cmd_group import group_command
from cmd_misc import help_command, start
from cmd_remind import remind_command
from cmd_view import all_birthdays, month_birthdays, view_birthdays, week_birthdays
from conv_add import add_conversation
from conv_edit import edit_conversation
from jobs import daily_birthday_check, monthly_birthday_list, weekly_birthday_list

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

TIMEZONE = ZoneInfo(os.environ.get("TIMEZONE", "Asia/Singapore"))


async def on_error(update, context):
    logger.exception("Unhandled exception while processing update %s", update, exc_info=context.error)


MAIN_COMMANDS = [
    BotCommand("add", "Add a birthday"),
    BotCommand("edit", "Edit an existing birthday"),
    BotCommand("delete", "Delete a birthday by ID"),
    BotCommand("week", "Birthdays this week"),
    BotCommand("month", "Birthdays this month"),
    BotCommand("all", "All birthdays, soonest first"),
    BotCommand("view", "View birthdays in one category"),
    BotCommand("group", "Manage birthday categories"),
    BotCommand("remind", "Link reminders to a group chat"),
    BotCommand("help", "Show what the bot can do"),
]


async def post_init(app: Application):
    # Populates Telegram's built-in "/" command menu, so tapping the message
    # input shows these as clickable suggestions instead of the user typing them.
    await app.bot.set_my_commands(MAIN_COMMANDS)


def build_app() -> Application:
    token = os.environ.get("BOT_TOKEN")
    if not token:
        raise RuntimeError(
            "BOT_TOKEN environment variable is not set. Get a token from @BotFather "
            "and set it before running the bot (see README.md)."
        )

    app = ApplicationBuilder().token(token).post_init(post_init).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(add_conversation)
    app.add_handler(edit_conversation)
    app.add_handler(CommandHandler("delete", delete_birthday))
    app.add_handler(CommandHandler("view", view_birthdays))
    app.add_handler(CommandHandler("week", week_birthdays))
    app.add_handler(CommandHandler("month", month_birthdays))
    app.add_handler(CommandHandler("all", all_birthdays))
    app.add_handler(CommandHandler("group", group_command))
    app.add_handler(CommandHandler("remind", remind_command))
    app.add_error_handler(on_error)

    # Daily at 00:00 local time: today\'s birthdays -> DM owners + linked groups.
    app.job_queue.run_daily(daily_birthday_check, time=time(0, 0, tzinfo=TIMEZONE), name="daily_birthday_check")
    # Every Monday at 00:00 local time: this week\'s birthdays -> DM owners.
    # NOTE: since python-telegram-bot v20, `days` uses 0=Sunday..6=Saturday, so Monday=1.
    app.job_queue.run_daily(
        weekly_birthday_list, time=time(0, 0, tzinfo=TIMEZONE), days=(1,), name="weekly_birthday_list"
    )
    # 1st of each month at 00:00 local time: full month list -> DM owners.
    app.job_queue.run_monthly(
        monthly_birthday_list, when=time(0, 0, tzinfo=TIMEZONE), day=1, name="monthly_birthday_list"
    )

    return app


def main():
    db.init_db()
    app = build_app()
    logger.info("Birthday bot starting (timezone=%s)...", TIMEZONE)
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
