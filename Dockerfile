FROM python:3.11-slim

WORKDIR /app

# ffmpeg is needed to convert Telegram voice notes (.ogg) before sending them
# to the speech-to-text API, which doesn't accept .ogg directly.
RUN apt-get update \
    && apt-get install -y --no-install-recommends ffmpeg \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Persist the SQLite DB on a mounted volume in production (see README).
ENV DB_PATH=/app/data/birthdays.db
RUN mkdir -p /app/data

CMD ["python", "bot.py"]
