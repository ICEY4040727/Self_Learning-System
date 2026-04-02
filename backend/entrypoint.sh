#!/bin/sh
set -e

echo "Running database migrations..."
cd /app/backend
if ! alembic upgrade head 2>&1; then
    echo "⚠️ Alembic migration failed, falling back to create_all..."
    cd /app
    python -c "from backend.db.database import init_db; init_db()"
else
    cd /app
fi

echo "Starting server..."
exec uvicorn backend.main:app --host 0.0.0.0 --port 8000
