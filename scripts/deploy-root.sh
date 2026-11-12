#!/usr/bin/env bash
set -euo pipefail
if [[ $# != 1 || ! $1 =~ ^deploy\ sha256:[0-9a-f]{64}$ ]]; then
  echo 'Only deploy sha256:<64 lowercase hexadecimal characters> is allowed.' >&2
  exit 2
fi
project_dir=/srv/projects/career_tracker
state_dir=/var/lib/career-tracker
[[ -s "$state_dir/database-restored" ]] || { echo 'Database has not been restored; deployment refused.' >&2; exit 1; }
[[ -f "$project_dir/.env" ]] || { echo 'Server environment file is missing.' >&2; exit 1; }
exec 9>/run/lock/career-tracker-deploy.lock
flock -n 9 || { echo 'Another deployment or restore is running.' >&2; exit 1; }
export CAREER_ENV_FILE="$project_dir/.env"
export CAREER_IMAGE="duzer61/career_tracker@${1#deploy }"
compose=(/usr/bin/docker compose --env-file /dev/null --project-directory "$project_dir" -p career_tracker -f /etc/career-tracker/compose.yml)
step() {
  local label=$1
  shift
  echo "$label"
  if ! "$@" >/dev/null 2>&1; then
    echo "$label failed. Raw output is suppressed to protect credentials. Existing data is retained." >&2
    exit 1
  fi
}
step 'Checking configuration' "${compose[@]}" config -q
step 'Pulling application image' "${compose[@]}" pull career
# Do not upgrade PostgreSQL or Redis images during an application deployment.
step 'Checking database services' "${compose[@]}" up -d --wait --wait-timeout 120 --pull never postgres redis
umask 077
backup_dir="$state_dir/backups"
mkdir -p "$backup_dir"
backup_file="$backup_dir/predeploy-$(date -u +%Y%m%dT%H%M%SZ)-$$.dump"
echo 'Saving database before migrations'
if ! "${compose[@]}" exec -T postgres sh -ec 'exec pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB" -Fc --no-owner --no-acl' >"$backup_file" 2>/dev/null; then
  echo 'Database backup failed; application update refused.' >&2
  exit 1
fi
[[ -s "$backup_file" ]] || { echo 'Empty database backup; update refused.' >&2; exit 1; }
# Stop only this application during migrations. PostgreSQL and Redis keep running.
step 'Stopping application for migrations' "${compose[@]}" stop career
step 'Running Alembic migrations' "${compose[@]}" run --rm --no-deps --entrypoint /app/.venv/bin/alembic career upgrade head
step 'Checking Alembic revision' "${compose[@]}" run --rm --no-deps --entrypoint /app/.venv/bin/alembic career current --check-heads
step 'Starting application' "${compose[@]}" up -d --no-deps --wait --wait-timeout 180 career
step 'Checking local HTTP endpoint' /usr/bin/curl --fail --silent --output /dev/null http://127.0.0.1:9500/
printf '%s\n' "$CAREER_IMAGE" >"$state_dir/current-image"
echo 'Career Tracker deployment completed.'
