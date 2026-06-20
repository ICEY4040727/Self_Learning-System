#!/bin/sh
set -e

echo "Running database migrations for patrol service..."
cd /app/backend
export PYTHONPATH=/app
if ! alembic upgrade head 2>&1; then
    echo "Alembic migration failed, falling back to create_all..."
    cd /app
    python -c "from backend.db.database import init_db; init_db()"
else
    cd /app
fi

echo "User LLM patrol scheduler starting..."
exec python -m backend.scripts.user_llm_patrol_scheduler
