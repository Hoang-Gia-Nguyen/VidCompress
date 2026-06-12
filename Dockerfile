# Dockerfile (UI‑only)
FROM python:3.12-slim

# System deps – only cron (optional) for future use
RUN apt-get update && apt-get install -y --no-install-recommends \
    cron \
 && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY . /app

# Install Flask (already in requirements.txt) and any other UI deps
RUN pip install --no-cache-dir -r requirements.txt

# Optional dummy crontab to keep cron available (not required for UI)
COPY cronjob_ui /etc/cron.d/ui-cron
RUN chmod 0644 /etc/cron.d/ui-cron && crontab /etc/cron.d/ui-cron

EXPOSE 5577
ENTRYPOINT ["python", "-m", "app.web"]
