"""/view, /week, /month, /all -- color-coded text-list views of birthdays.

/view is scoped to a single category: `/view group <name>`.
/week, /month, /all cover the other views (these used to live under /view).
"""

import calendar
from datetime import date

from telegram import Update
from telegram.ext import ContextTypes

import db
from birthday_calc import next_occurrence_delta, occurrence_in_range, week_bounds
from colors import GOOGLE_CALENDAR_COLORS


def _format_entry(b, today, date_override=None):
    c = GOOGLE_CALENDAR_COLORS[b["color_id"]]
    age = ""
    if b["year"]:
        target_year = today.year if (b["month"], b["day"]) >= (today.month, today.day) else today.year + 1
        age = f" (turns {target_year - b['year']})"
    if date_override is not None:
        date_str = date_override.strftime("%a %d %b")
    else:
        date_str = f"{b['day']:02d} {calendar.month_abbr[b['month']]}"
    group_str = f" \u00b7 _{b['group_name']}_" if b.get("group_name") else ""
    id_str = f" [#{b['id']}]"
    return f"{c['emoji']} *{date_str}* \u2014 {b['name']}{age}{group_str}{id_str}"


async def _require_private(update: Update) -> bool:
    if update.effective_chat.type != "private":
        await update.message.reply_text("Please DM me to view your birthdays.")
        return False
    return True


async def view_birthdays(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/view group <name> -- the only supported form now. Other views live
    under /week, /month, and /all."""
    if not await _require_private(update):
        return
    owner_id = update.effective_user.id
    args = context.args
    today = date.today()

    if len(args) < 2 or args[0].lower() != "group":
        await update.message.reply_text(
            "Usage: /view group <category name>\n\n"
            "For other views, try /week (this week), /month (this month), or /all (everyone)."
        )
        return

    gname = " ".join(args[1:])
    g = db.get_group_by_name(owner_id, gname)
    if not g:
        await update.message.reply_text(f"No category named \'{gname}\'. Check /group list.")
        return

    rows = db.list_birthdays(owner_id, group_id=g["id"])
    if not rows:
        await update.message.reply_text(f"No birthdays in category \'{g['name']}\' yet.")
        return

    rows.sort(key=lambda b: next_occurrence_delta(today, b["month"], b["day"]))
    lines = [f"\U0001F4C5 Birthdays in category \'{g['name']}\'", ""] + [_format_entry(b, today) for b in rows]
    await update.message.reply_text("\n".join(lines), parse_mode="Markdown")


async def all_birthdays(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/all -- every birthday, soonest upcoming first."""
    if not await _require_private(update):
        return
    owner_id = update.effective_user.id
    today = date.today()

    rows = db.list_birthdays(owner_id)
    if not rows:
        await update.message.reply_text("No birthdays saved yet. Add one with /add.")
        return

    rows.sort(key=lambda b: next_occurrence_delta(today, b["month"], b["day"]))
    lines = ["\U0001F4C5 All birthdays (soonest first)", ""] + [_format_entry(b, today) for b in rows]
    await update.message.reply_text("\n".join(lines), parse_mode="Markdown")


async def month_birthdays(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/month -- birthdays in the current calendar month."""
    if not await _require_private(update):
        return
    owner_id = update.effective_user.id
    today = date.today()

    rows = db.list_birthdays(owner_id, month=today.month)
    if not rows:
        await update.message.reply_text(f"No birthdays in {calendar.month_name[today.month]}.")
        return

    rows.sort(key=lambda b: b["day"])
    lines = [f"\U0001F4C5 Birthdays this month ({calendar.month_name[today.month]})", ""] + [
        _format_entry(b, today) for b in rows
    ]
    await update.message.reply_text("\n".join(lines), parse_mode="Markdown")


async def week_birthdays(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/week -- birthdays in the current week (Monday-Sunday)."""
    if not await _require_private(update):
        return
    owner_id = update.effective_user.id
    today = date.today()
    monday, sunday = week_bounds(today)

    rows = db.list_birthdays(owner_id)
    week_rows = []
    for b in rows:
        occurrence = occurrence_in_range(b["month"], b["day"], monday, sunday)
        if occurrence is not None:
            week_rows.append((occurrence, b))

    label = f"{monday.strftime('%d %b')}\u2013{sunday.strftime('%d %b')}"
    if not week_rows:
        await update.message.reply_text(f"No birthdays this week ({label}).")
        return

    week_rows.sort(key=lambda pair: pair[0])
    lines = [f"\U0001F4C5 Birthdays this week ({label})", ""] + [
        _format_entry(b, today, date_override=occurrence) for occurrence, b in week_rows
    ]
    await update.message.reply_text("\n".join(lines), parse_mode="Markdown")
