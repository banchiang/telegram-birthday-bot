"""Scheduled jobs: the daily midnight birthday check (DMs + linked group
posts), the Monday weekly list DM, and the start-of-month full list DM.
"""

import logging
from datetime import date

import db
from birthday_calc import occurrence_in_range, week_bounds
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
        lines = [f"\U0001F382 *Birthday reminder \u2014 {today.strftime('%d %b')}*", ""]
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
        lines = [f"\U0001F382 *Birthday reminder \u2014 {target['group_name']}*", ""]
        for b in todays:
            c = GOOGLE_CALENDAR_COLORS[b["color_id"]]
            lines.append(f"{c['emoji']} *{b['name']}*{_age_suffix(today, b)}")
        try:
            await bot.send_message(chat_id=target["chat_id"], text="\n".join(lines), parse_mode="Markdown")
        except Exception:
            logger.exception("Failed to post daily reminder to chat %s", target["chat_id"])


async def weekly_birthday_list(context):
    """Runs Mondays at 00:00: DM each owner that week\'s birthdays."""
    today = date.today()
    monday, sunday = week_bounds(today)
    bot = context.bot

    for owner_id in db.list_owners():
        rows = db.list_birthdays(owner_id)
        week_rows = []
        for b in rows:
            occurrence = occurrence_in_range(b["month"], b["day"], monday, sunday)
            if occurrence is not None:
                week_rows.append((occurrence, b))
        if not week_rows:
            continue
        week_rows.sort(key=lambda pair: pair[0])
        label = f"{monday.strftime('%d %b')}\u2013{sunday.strftime('%d %b')}"
        lines = [f"\U0001F4C5 *Birthdays this week ({label})*", ""]
        for occurrence, b in week_rows:
            c = GOOGLE_CALENDAR_COLORS[b["color_id"]]
            group_str = f" \u00b7 _{b['group_name']}_" if b.get("group_name") else ""
            lines.append(f"{c['emoji']} {occurrence.strftime('%a %d %b')} \u2014 *{b['name']}*{group_str}")
        try:
            await bot.send_message(chat_id=owner_id, text="\n".join(lines), parse_mode="Markdown")
        except Exception:
            logger.exception("Failed to DM weekly list to owner %s", owner_id)


async def monthly_birthday_list(context):
    today = date.today()
    bot = context.bot

    for owner_id in db.list_owners():
        items = db.birthdays_in_month(owner_id, today.month)
        if not items:
            continue
        lines = [f"\U0001F4C5 *Birthdays this month \u2014 {today.strftime('%B')}*", ""]
        for b in sorted(items, key=lambda r: r["day"]):
            c = GOOGLE_CALENDAR_COLORS[b["color_id"]]
            group_str = f" \u00b7 _{b['group_name']}_" if b.get("group_name") else ""
            lines.append(f"{c['emoji']} {b['day']:02d} {today.strftime('%b')} \u2014 *{b['name']}*{group_str}")
        try:
            await bot.send_message(chat_id=owner_id, text="\n".join(lines), parse_mode="Markdown")
        except Exception:
            logger.exception("Failed to DM monthly list to owner %s", owner_id)
