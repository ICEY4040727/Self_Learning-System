#!/bin/sh
set -e

echo "Running database migrations..."
cd /app/backend
export PYTHONPATH=/app
if ! alembic upgrade head 2>&1; then
    echo "⚠️ Alembic migration failed, falling back to create_all..."
    cd /app
    python -c "from backend.db.database import init_db; init_db()"
else
    cd /app
fi

echo "Starting server..."
exec uvicorn backend.main:app --host "${APP_HOST:-0.0.0.0}" --port "${APP_PORT:-8000}" --reload
