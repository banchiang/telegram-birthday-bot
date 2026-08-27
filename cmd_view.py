"""/view — text-list "calendar" of birthdays, color-coded with Google Calendar colors."""

import calendar
from datetime import date

from telegram import Update
from telegram.ext import ContextTypes

import db
from colors import GOOGLE_CALENDAR_COLORS

MONTH_NAMES = {calendar.month_name[i].lower(): i for i in range(1, 13)}
MONTH_ABBR = {calendar.month_abbr[i].lower(): i for i in range(1, 13)}


def _next_occurrence_delta(today: date, month: int, day: int) -> int:
    """Days from today until the next time this month/day occurs (0 = today)."""
    year = today.year
    try:
        candidate = date(year, month, day)
    except ValueError:
        candidate = date(year, month, 28)  # Feb 29 fallback in non-leap years
    if candidate < today:
        try:
            candidate = date(year + 1, month, day)
        except ValueError:
            candidate = date(year + 1, month, 28)
    return (candidate - today).days


def _format_entry(b, today, show_date=True):
    c = GOOGLE_CALENDAR_COLORS[b["color_id"]]
    age = ""
    if b["year"]:
        target_year = today.year if (b["month"], b["day"]) >= (today.month, today.day) else today.year + 1
        # if birthday already passed this year, they'll turn (target_year - birth_year)
        age = f" (turns {target_year - b['year']})"
    date_str = f"{b['day']:02d} {calendar.month_abbr[b['month']]}" if show_date else ""
    group_str = f" · _{b['group_name']}_" if b.get("group_name") else ""
    id_str = f" [#{b['id']}]"
    if show_date:
        return f"{c['emoji']} *{date_str}* — {b['name']}{age}{group_str}{id_str}"
    return f"{c['emoji']} {b['name']}{age}{group_str}{id_str}"


async def view_birthdays(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.type != "private":
        await update.message.reply_text("Please DM me to view your birthdays.")
        return
    owner_id = update.effective_user.id
    args = context.args
    today = date.today()

    group_filter = None
    month_filter = None

    if args:
        if args[0].lower() == "group" and len(args) > 1:
            gname = " ".join(args[1:])
            g = db.get_group_by_name(owner_id, gname)
            if not g:
                await update.message.reply_text(f"No category named '{gname}'. Check /group list.")
                return
            group_filter = g
        else:
            token = args[0].lower()
            month_filter = MONTH_NAMES.get(token) or MONTH_ABBR.get(token)
            if month_filter is None and token.isdigit() and 1 <= int(token) <= 12:
                month_filter = int(token)
            if month_filter is None:
                await update.message.reply_text(
                    "Usage: /view, /view <month name or number>, or /view group <category name>"
                )
                return

    rows = db.list_birthdays(
        owner_id,
        month=month_filter,
        group_id=group_filter["id"] if group_filter else None,
    )

    if not rows:
        await update.message.reply_text("No birthdays saved yet. Add one with /add.")
        return

    if month_filter:
        title = f"📅 Birthdays in {calendar.month_name[month_filter]}"
        rows.sort(key=lambda b: b["day"])
        lines = [title, ""] + [_format_entry(b, today) for b in rows]
    elif group_filter:
        title = f"📅 Birthdays in category '{group_filter['name']}'"
        rows.sort(key=lambda b: _next_occurrence_delta(today, b["month"], b["day"]))
        lines = [title, ""] + [_format_entry(b, today) for b in rows]
    else:
        title = "📅 All birthdays (soonest first)"
        rows.sort(key=lambda b: _next_occurrence_delta(today, b["month"], b["day"]))
        lines = [title, ""] + [_format_entry(b, today) for b in rows]

    await update.message.reply_text("\n".join(lines), parse_mode="Markdown")
