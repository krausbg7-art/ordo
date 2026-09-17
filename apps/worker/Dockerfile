# Собирается с контекстом = корень репозитория (см. docker-compose.yml)
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential libmagic1 libpq-dev curl poppler-utils \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY apps/api /app/api
COPY apps/worker /app/worker

RUN pip install --no-cache-dir -e "/app/api[dev]" \
    && pip install --no-cache-dir -e "/app/worker[dev]"

WORKDIR /app/worker

CMD ["arq", "ordo_worker.main.WorkerSettings"]
