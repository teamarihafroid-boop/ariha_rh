# Build the React app first, then serve it from the FastAPI service itself
# (see backend/app/main.py's SPA fallback) — one Railway service, one origin,
# no separate frontend host or extra CORS to manage.

FROM node:20-alpine AS frontend-build
WORKDIR /src/frontend
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

FROM python:3.11-slim AS backend
WORKDIR /app

# postgresql-client gives us pg_dump for app/scripts/backup_db.py, run as a
# separate Railway Cron Job sharing this same image — see docs/DEPLOYMENT.md.
RUN apt-get update && apt-get install -y --no-install-recommends postgresql-client \
    && rm -rf /var/lib/apt/lists/*

COPY backend/pyproject.toml ./
COPY backend/app ./app
RUN pip install --no-cache-dir .

COPY backend/alembic ./alembic
COPY backend/alembic.ini ./

COPY --from=frontend-build /src/frontend/dist ./web

ENV PYTHONUNBUFFERED=1
EXPOSE 8000

# Migrations run on every boot, before the app starts serving — Railway
# restarts the container on every deploy, so this is the natural hook point
# rather than a separate manual step.
CMD ["sh", "-c", "python -m alembic upgrade head && python -m uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
