"""Scheduled jobs: the daily midnight birthday check (DMs + linked group
posts) and the start-of-month full list DM.
"""

import logging
from datetime import date

import db
from colors import GOOGLE_CALENDAR_COLORS

logger = logging.getLogger(__name__)


def _age_suffix(today, b):
    if not b["year"]:
        return ""
    return f" (turns {today.year - b['year']})"


async def daily_birthday_check(context):
    today = date.today()
    bot = context.bot

    for owner_id in db.list_owners():
        todays = db.birthdays_on(owner_id, today.month, today.day)
        if not todays:
            continue
        lines = [f"🎂 *Birthday reminder — {today.strftime('%d %b')}*", ""]
        for b in todays:
            c = GOOGLE_CALENDAR_COLORS[b["color_id"]]
            lines.append(f"{c['emoji']} *{b['name']}*{_age_suffix(today, b)}")
        try:
            await bot.send_message(chat_id=owner_id, text="\n".join(lines), parse_mode="Markdown")
        except Exception:
            logger.exception("Failed to DM daily reminder to owner %s", owner_id)

    for target in db.list_all_remind_targets():
        todays = db.birthdays_on_in_group(target["group_id"], today.month, today.day)
        if not todays:
            continue
        lines = [f"🎂 *Birthday reminder — {target['group_name']}*", ""]
        for b in todays:
            c = GOOGLE_CALENDAR_COLORS[b["color_id"]]
            lines.append(f"{c['emoji']} *{b['name']}*{_age_suffix(today, b)}")
        try:
            await bot.send_message(chat_id=target["chat_id"], text="\n".join(lines), parse_mode="Markdown")
        except Exception:
            logger.exception("Failed to post daily reminder to chat %s", target["chat_id"])


async def monthly_birthday_list(context):
    today = date.today()
    bot = context.bot

    for owner_id in db.list_owners():
        items = db.birthdays_in_month(owner_id, today.month)
        if not items:
            continue
        lines = [f"📅 *Birthdays this month — {today.strftime('%B')}*", ""]
        for b in sorted(items, key=lambda r: r["day"]):
            c = GOOGLE_CALENDAR_COLORS[b["color_id"]]
            group_str = f" · _{b['group_name']}_" if b.get("group_name") else ""
            lines.append(f"{c['emoji']} {b['day']:02d} {today.strftime('%b')} — *{b['name']}*{group_str}")
        try:
            await bot.send_message(chat_id=owner_id, text="\n".join(lines), parse_mode="Markdown")
        except Exception:
            logger.exception("Failed to DM monthly list to owner %s", owner_id)
