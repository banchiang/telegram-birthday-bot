"""/remind — link a Telegram group chat to a birthday category so the bot
posts a reminder there at midnight when someone in that category has a
birthday.
"""

from telegram import Update
from telegram.ext import ContextTypes

import db

HELP_TEXT = (
    "*Group reminder commands:*\n"
    "Run these *inside the Telegram group* you want reminders posted to "
    "(make sure I've been added to that group first):\n\n"
    "/remind link <category> — post reminders here for that category\n"
    "/remind unlink <category> — stop posting reminders here for that category\n\n"
    "Run this one in a private chat with me:\n"
    "/remind list — see every group you've linked"
)


async def remind_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    owner_id = update.effective_user.id
    chat = update.effective_chat
    args = context.args

    if not args:
        await update.message.reply_text(HELP_TEXT, parse_mode="Markdown")
        return

    sub = args[0].lower()

    if sub == "list":
        targets = db.list_remind_targets(owner_id)
        if not targets:
            await update.message.reply_text("You haven't linked any groups yet. See /remind for how.")
            return
        lines = ["*Linked groups:*"] + [
            f"• {t['chat_title'] or t['chat_id']} → category '{t['group_name']}'" for t in targets
        ]
        await update.message.reply_text("\n".join(lines), parse_mode="Markdown")
        return

    if sub in ("link", "unlink") and len(args) > 1:
        if chat.type not in ("group", "supergroup"):
            await update.message.reply_text(
                "Run /remind link (or unlink) *inside the group chat* you want to connect, not in DM.",
                parse_mode="Markdown",
            )
            return
        name = " ".join(args[1:])
        g = db.get_group_by_name(owner_id, name)
        if not g:
            await update.message.reply_text(
                f"You don't have a category named '{name}'. Create one via DM with /group create {name} first."
            )
            return
        if sub == "link":
            db.add_remind_target(owner_id, g["id"], chat.id, chat.title)
            await update.message.reply_text(
                f"✅ This group will now get a reminder here whenever someone in '{g['name']}' has a birthday, "
                "posted at midnight on the day."
            )
        else:
            ok = db.remove_remind_target(owner_id, g["id"], chat.id)
            if ok:
                await update.message.reply_text(f"Unlinked '{g['name']}' from this group.")
            else:
                await update.message.reply_text(f"'{g['name']}' wasn't linked to this group.")
        return

    await update.message.reply_text(HELP_TEXT, parse_mode="Markdown")
