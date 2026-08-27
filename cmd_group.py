"""/group — create, list, delete categories and assign birthdays to them."""

from telegram import Update
from telegram.ext import ContextTypes

import db

HELP_TEXT = (
    "*Category commands:*\n"
    "/group create <name> — create a new category\n"
    "/group list — list your categories\n"
    "/group assign <birthday\\_id> <name> — put a birthday into a category\n"
    "/group delete <name> — delete a category (birthdays stay, just uncategorized)"
)


async def group_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.type != "private":
        await update.message.reply_text("Please DM me to manage categories.")
        return
    owner_id = update.effective_user.id
    args = context.args

    if not args:
        await update.message.reply_text(HELP_TEXT, parse_mode="Markdown")
        return

    sub = args[0].lower()

    if sub == "create" and len(args) > 1:
        name = " ".join(args[1:])
        group_id = db.create_group(owner_id, name)
        if group_id is None:
            await update.message.reply_text(f"You already have a category named '{name}'.")
        else:
            await update.message.reply_text(f"✅ Created category '{name}' (ID {group_id}).")
        return

    if sub == "list":
        groups = db.list_groups(owner_id)
        if not groups:
            await update.message.reply_text("You don't have any categories yet. Create one with /group create <name>.")
            return
        lines = ["*Your categories:*"] + [f"• {g['name']} — {g['count']} birthday(s)" for g in groups]
        await update.message.reply_text("\n".join(lines), parse_mode="Markdown")
        return

    if sub == "assign" and len(args) > 2 and args[1].isdigit():
        bday_id = int(args[1])
        name = " ".join(args[2:])
        b = db.get_birthday(owner_id, bday_id)
        if not b:
            await update.message.reply_text(f"No birthday with ID {bday_id} found.")
            return
        g = db.get_group_by_name(owner_id, name)
        if not g:
            await update.message.reply_text(f"No category named '{name}'. Create it first with /group create {name}.")
            return
        db.assign_group(owner_id, bday_id, g["id"])
        await update.message.reply_text(f"✅ {b['name']} is now in category '{g['name']}'.")
        return

    if sub == "delete" and len(args) > 1:
        name = " ".join(args[1:])
        ok = db.delete_group(owner_id, name)
        if ok:
            await update.message.reply_text(f"🗑️ Deleted category '{name}'.")
        else:
            await update.message.reply_text(f"No category named '{name}'.")
        return

    await update.message.reply_text(HELP_TEXT, parse_mode="Markdown")
