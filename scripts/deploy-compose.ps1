# Rebuild and restart the compose stack (includes user-llm-patrol).
$ErrorActionPreference = "Stop"
Set-Location (Join-Path $PSScriptRoot "..")

if (-not (Test-Path ".env")) {
    Copy-Item ".env.example" ".env"
    Write-Host "Created .env from .env.example — review SECRET_KEY before production."
}

Write-Host "Building and starting compose stack..."
docker compose up -d --build

Write-Host "Waiting for backend health..."
$healthy = $false
for ($i = 1; $i -le 40; $i++) {
    try {
        $resp = Invoke-WebRequest -Uri "http://127.0.0.1:8000/health" -UseBasicParsing -TimeoutSec 3
        if ($resp.StatusCode -eq 200) { $healthy = $true; break }
    } catch {}
    Start-Sleep -Seconds 3
}

if (-not $healthy) {
    Write-Error "Backend did not become healthy in time."
}

Write-Host "Compose services:"
docker compose ps

Write-Host "`nPatrol scheduler logs:"
docker compose logs user-llm-patrol --tail=20

if ((docker compose logs user-llm-patrol --tail=50) -notmatch "User LLM patrol scheduler active") {
    Write-Error "user-llm-patrol did not start the scheduler."
}

Write-Host "`nDeploy complete. Optional immediate patrol:"
Write-Host "  docker compose exec user-llm-patrol python -m backend.scripts.audit_user_llm_consistency_job --sql --repair --fail-on-issues"
