"""Entry point: wires up all handlers and the two scheduled jobs, then runs
the bot with long-polling.
"""

import logging
import os
from datetime import time
from zoneinfo import ZoneInfo

from telegram import Update
from telegram.ext import Application, ApplicationBuilder, CommandHandler

import db
from cmd_delete import delete_birthday
from cmd_group import group_command
from cmd_misc import help_command, start
from cmd_remind import remind_command
from cmd_view import view_birthdays
from conv_add import add_conversation
from jobs import daily_birthday_check, monthly_birthday_list

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

TIMEZONE = ZoneInfo(os.environ.get("TIMEZONE", "Asia/Singapore"))


async def on_error(update, context):
    logger.exception("Unhandled exception while processing update %s", update, exc_info=context.error)


def build_app() -> Application:
    token = os.environ.get("BOT_TOKEN")
    if not token:
        raise RuntimeError(
            "BOT_TOKEN environment variable is not set. Get a token from @BotFather "
            "and set it before running the bot (see README.md)."
        )

    app = ApplicationBuilder().token(token).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(add_conversation)
    app.add_handler(CommandHandler("delete", delete_birthday))
    app.add_handler(CommandHandler("view", view_birthdays))
    app.add_handler(CommandHandler("group", group_command))
    app.add_handler(CommandHandler("remind", remind_command))
    app.add_error_handler(on_error)

    # Daily at 00:00 local time: today's birthdays -> DM owners + linked groups.
    app.job_queue.run_daily(daily_birthday_check, time=time(0, 0, tzinfo=TIMEZONE), name="daily_birthday_check")
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
