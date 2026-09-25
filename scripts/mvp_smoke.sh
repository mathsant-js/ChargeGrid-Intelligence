#!/usr/bin/env bash
set -Eeuo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
COMPOSE_FILE="$ROOT_DIR/docker-compose.mvp-smoke.yml"
PROJECT_NAME="chargegrid-mvp-smoke-$$"
CURRENT_STAGE="initialization"

export MVP_SMOKE_POSTGRES_DB="chargegrid_smoke"
export MVP_SMOKE_POSTGRES_USER="chargegrid_smoke"
export MVP_SMOKE_POSTGRES_PASSWORD="$(python3 -c 'import secrets; print(secrets.token_urlsafe(24))')"
export MVP_SMOKE_JWT_SECRET="$(python3 -c 'import secrets; print(secrets.token_urlsafe(48))')"
export DEMO_ADMIN_PASSWORD="$(python3 -c 'import secrets; print(secrets.token_urlsafe(18))')"
export DEMO_USER_PASSWORD="$(python3 -c 'import secrets; print(secrets.token_urlsafe(18))')"
export MVP_SMOKE_BACKEND_PORT="${MVP_SMOKE_BACKEND_PORT:-18000}"
export MVP_SMOKE_FRONTEND_PORT="${MVP_SMOKE_FRONTEND_PORT:-15173}"
export DEMO_API_URL="http://127.0.0.1:${MVP_SMOKE_BACKEND_PORT}/api/v1"
export DEMO_FRONTEND_URL="http://127.0.0.1:${MVP_SMOKE_FRONTEND_PORT}"

compose() {
  docker compose --project-name "$PROJECT_NAME" --file "$COMPOSE_FILE" "$@"
}

cleanup() {
  local exit_code=$?
  trap - EXIT
  echo "[cleanup] Removing only Compose project: $PROJECT_NAME"
  compose down --volumes --remove-orphans --timeout 10 || true
  if (( exit_code != 0 )); then
    echo "[failed] Stage: $CURRENT_STAGE" >&2
  fi
  exit "$exit_code"
}

run_stage() {
  CURRENT_STAGE="$1"
  shift
  echo "[stage] $CURRENT_STAGE"
  "$@"
}

trap cleanup EXIT
trap 'exit 130' INT TERM

run_stage "Docker availability" docker info
run_stage "Compose configuration" compose config --quiet
run_stage "Build application images" compose build backend frontend
run_stage "Start isolated PostgreSQL 16" compose up --detach --wait db
run_stage "Apply migrations" compose run --rm backend alembic upgrade head
run_stage "Verify alembic current" compose run --rm backend alembic current --check-heads
run_stage "Verify alembic metadata" compose run --rm backend alembic check
run_stage "Execute deterministic seed" compose run --rm backend python -m app.demo_seed
run_stage "Prepare ML artifact and causal history" compose run --rm backend \
  python -m app.ml.demo_prepare --demo-start 2026-09-18T11:58:00+00:00
run_stage "Start real backend and frontend" compose up --detach --wait backend frontend
run_stage "Execute public-API Golden Path" python3 "$ROOT_DIR/scripts/sprint3_demo.py"
run_stage "Confirm service health" compose ps --status running

echo "[passed] ChargeGrid Intelligence MVP smoke test completed successfully."
