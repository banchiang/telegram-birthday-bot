# Birthday Reminder Bot

A Telegram bot that tracks birthdays with Google-Calendar-style colors, reminds
you automatically, and can post category-based reminders into a group chat.

## Features

- `/add` — add a birthday (name, date of birth, color from 21 color options,
  optional category). When it asks for the date, you can type it or send a
  **voice note** saying it instead — no typing required for that step (see
  section 1b)
- `/edit` — lists all your birthdays with their IDs, then lets you pick one
  and update its name, date, and color — prompted the same way as `/add`
  (voice note works for the date step here too)
- `/delete <id>` — remove a birthday by its ID
- `/week`, `/month`, `/all` — list birthdays this week, this month, or every
  birthday (soonest first), all color-coded
- `/view group <name>` — list birthdays in one category
- Automatic daily reminder at **00:00** (default timezone: `Asia/Singapore`)
  DMing you if anyone has a birthday that day
- Automatic reminder every **Monday** at 00:00 with that week's birthdays
- Automatic reminder on the **1st of every month** at 00:00 with the full
  list of that month's birthdays
- `/group` — create/list/assign/delete categories to group birthdays
  (e.g. "Family", "Work", "Uni Friends")
- `/remind link <category>` — run inside a Telegram group you've added the
  bot to, so that group also gets a midnight post whenever someone in that
  category has a birthday

All data is scoped per Telegram user, so if you ever add a friend to the
same bot, your birthdays and theirs won't mix.

---

## 1. Create your bot with @BotFather (2 minutes)

1. In Telegram, open a chat with **[@BotFather](https://t.me/BotFather)**.
2. Send `/newbot`.
3. Give it a display name (e.g. `Birthday Reminders`) — this is what shows
   in chats.
4. Give it a username ending in `bot` (e.g. `johnny_birthday_bot`) — must be
   globally unique.
5. BotFather replies with a token that looks like
   `123456789:AAExxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx`. **Save this token** —
   it's the only credential you need, and it's the last time BotFather shows
   it to you in full.
6. Optional polish: send BotFather `/setdescription`, `/setabouttext`, or
   `/setuserpic` and follow the prompts to customize your bot's profile.
7. Open a DM with your new bot and press **Start** (or send `/start`) once —
   this is required before the bot is allowed to message you first.

That's it — no other Telegram-side setup is needed. The bot works via
long-polling, so you don't need to register a webhook URL or open any ports.

---

## 1b. Voice-note date entry (free, no setup needed)

When `/add` or `/edit` asks for the date of birth, you can send a voice note
instead of typing — just say the date, e.g. *"March 3rd 1995"* or *"25
December"*. The name is still typed and the color is still picked with the
button keyboard, exactly as before; voice only replaces the date step.

Voice works out of the box — no API key, no account, no extra step needed.

Under the hood: the bot downloads the voice note and transcribes it locally
using [faster-whisper](https://github.com/SYSTRAN/faster-whisper) (an
efficient, open-source speech-to-text model that runs on the bot's own
server — nothing is sent to any third party), then a small built-in
rule-based parser pulls the date out of the transcript with no external API
call either. The whole feature costs $0 to run, however much you use it.

**Trade-offs versus a paid AI service, worth knowing:**
- The default model (`base`, ~75MB) is fast and works well for clear speech,
  but can stumble on unusual accents or noisy audio — a bigger model
  (`WHISPER_MODEL_SIZE=small` or `medium` in your environment variables) is
  more accurate but slower and needs more RAM.
- The date parser understands month names, "25 December", "3rd of March",
  and numeric `DD-MM` / `DD-MM-YYYY` — but very unusual phrasing may not
  parse. If it can't find a valid date in what you said, it tells you what
  it heard and asks you to try again or type the date instead.
- The first voice note after each deploy/restart takes a little longer,
  since the model downloads and loads into memory on first use; after that
  it stays loaded and responds quickly.

---

## 2. Run it locally (optional, to test before deploying)

Requires Python 3.11+.

```bash
cd telegram-birthday-bot
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

export BOT_TOKEN="paste-your-botfather-token-here"
export TIMEZONE="Asia/Singapore"   # optional, this is already the default

python bot.py
```

You should see `Birthday bot starting...` in the console. Message your bot
on Telegram and try `/start`.

Stop it with Ctrl+C. Note: reminders only fire while the process is
running, which is why step 3 (deploying somewhere that stays on) matters.

---

## 3. Deploy so it runs 24/7 (Railway)

Railway is a good fit here: it's cheap for a small always-on worker, and
supports a persistent disk so your birthdays survive redeploys.

1. Push this folder to a new GitHub repo (or use Railway's CLI to deploy the
   folder directly — see their docs for `railway up`).
2. On [railway.app](https://railway.app), create a **New Project → Deploy
   from GitHub repo**, and pick this repo. Railway will detect the
   `Dockerfile` and build it automatically.
3. In the service's **Variables** tab, add:
   - `BOT_TOKEN` = your BotFather token
   - `TIMEZONE` = `Asia/Singapore` (or omit — that's already the default)
   - (optional) `WHISPER_MODEL_SIZE` — only if you want a bigger/more
     accurate voice-transcription model than the default; see section 1b
4. In the service's **Settings → Volumes**, add a volume mounted at
   `/app/data`. This is what makes your birthdays persist across restarts
   and redeploys (without it, SQLite data would live only in the
   container's ephemeral filesystem).
5. Deploy. Check the **Deployments → Logs** tab for `Birthday bot
   starting...` to confirm it's running.
6. Message your bot on Telegram — it should respond immediately.

The same Dockerfile works unchanged on Render ("Background Worker" service
type — not "Web Service", since this bot doesn't listen on a port) or
Fly.io (`fly launch`, then `fly volumes create data` and mount it at
`/app/data`); the only two things that differ per host are how you set the
`BOT_TOKEN` environment variable and how you attach a persistent volume at
`/app/data`.

---

## Command reference

```
/start, /help          Show what the bot can do
/add                   Add a birthday (guided: name -> date -> color -> category)
                        date step accepts a typed value or a voice note
/edit                  Lists your birthdays with IDs, then edit one by ID
                        (guided: name -> date -> color, same as /add)
/delete <id>           Delete a birthday by ID (IDs are shown in /week, /month, /all, /view, /edit)
/week                  Birthdays this week (Monday-Sunday)
/month                 Birthdays this calendar month
/all                   All birthdays, soonest upcoming first
/view group <name>     Birthdays in one category (the only form /view supports)

/group create <name>   New category, e.g. /group create Family
/group list            List your categories
/group assign <id> <name>   Put birthday <id> into category <name>
/group delete <name>   Delete a category (birthdays stay, just uncategorized)

/remind                Show group-linking instructions
/remind link <name>    (run inside a group) start posting that category's
                        birthdays in this group at midnight
/remind unlink <name>  (run inside a group) stop
/remind list           (DM) see every group you've linked
```

Dates are entered as `DD-MM-YYYY` (e.g. `25-12-1990`) or `DD-MM` if you'd
rather not store the year (age won't be shown for those) — or spoken as a
voice note during `/add` or `/edit`.

When adding or editing a birthday you can pick from 21 colors: the 11
official Google Calendar colors plus 10 extra popular ones (Red, Black,
White, Brown, Turquoise, Pink, Gold, Navy, Mint, Coral).

## Notes / limitations

- The bot can only DM you first after you've sent it `/start` at least once
  — this is a Telegram platform rule, not a bug.
- To use `/remind link`, add the bot to the target group first (as a
  regular member is enough — it just needs permission to send messages).
- SQLite is used for simplicity; it's more than enough for personal or
  small-group use. If you ever need multi-instance scaling, swap `db.py`
  for Postgres.
