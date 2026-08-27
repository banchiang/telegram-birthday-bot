FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Persist the SQLite DB on a mounted volume in production (see README).
ENV DB_PATH=/app/data/birthdays.db
RUN mkdir -p /app/data

CMD ["python", "bot.py"]
