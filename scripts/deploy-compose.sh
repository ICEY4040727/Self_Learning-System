#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

if [[ ! -f .env ]]; then
  cp .env.example .env
  echo "Created .env from .env.example — review SECRET_KEY before production."
fi

echo "Building and starting compose stack..."
docker compose up -d --build

echo "Waiting for backend health..."
for i in $(seq 1 40); do
  if curl -sf http://127.0.0.1:8000/health >/dev/null; then
    break
  fi
  sleep 3
done

curl -sf http://127.0.0.1:8000/health >/dev/null || {
  echo "Backend did not become healthy in time." >&2
  exit 1
}

echo "Compose services:"
docker compose ps

echo
echo "Patrol scheduler logs:"
docker compose logs user-llm-patrol --tail=20

docker compose logs user-llm-patrol --tail=50 | grep -q "User LLM patrol scheduler active" || {
  echo "user-llm-patrol did not start the scheduler." >&2
  exit 1
}

echo
echo "Deploy complete. Optional immediate patrol:"
echo "  docker compose exec user-llm-patrol python -m backend.scripts.audit_user_llm_consistency_job --sql --repair --fail-on-issues"
