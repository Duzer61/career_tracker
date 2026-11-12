#!/usr/bin/env bash
set -euo pipefail
[[ $# == 0 ]] || { echo 'This restore command takes no arguments.' >&2; exit 2; }
project_dir=/srv/projects/career_tracker
state_dir=/var/lib/career-tracker
dump_file="$project_dir/restore/career_db.dump"
expected_sha256=361945ea93d60ca523aa3cf2fbc68cec89083d0c480ad8b2b8f56e3f5896af42
[[ ! -e "$state_dir/database-restored" ]] || { echo 'Database already restored; refusing to import again.' >&2; exit 1; }
[[ -f "$project_dir/.env" && -f "$dump_file" ]] || { echo 'Environment file or dump missing.' >&2; exit 1; }
actual_sha256=$(sha256sum "$dump_file")
[[ ${actual_sha256%% *} == "$expected_sha256" ]] || { echo 'Dump checksum mismatch; stopped.' >&2; exit 1; }
exec 9>/run/lock/career-tracker-deploy.lock
flock -n 9 || { echo 'Another deployment or restore is running.' >&2; exit 1; }
export CAREER_ENV_FILE="$project_dir/.env"
compose=(/usr/bin/docker compose --env-file /dev/null --project-directory "$project_dir" -p career_tracker -f /etc/career-tracker/compose.yml)
if ! "${compose[@]}" up -d --wait --wait-timeout 120 postgres >/dev/null 2>&1; then
  echo 'PostgreSQL startup failed; raw output suppressed.' >&2; exit 1
fi
query() {
  "${compose[@]}" exec -T postgres sh -ec 'exec psql -X -v ON_ERROR_STOP=1 -U "$POSTGRES_USER" -d "$POSTGRES_DB" -At' 2>/dev/null
}
# Covers every user schema, including extension or partitioned tables.
table_count=$(query <<'SQL'
SELECT count(*) FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace WHERE c.relkind IN ('r','p','v','m','f','S') AND n.nspname NOT IN ('pg_catalog','information_schema') AND n.nspname NOT LIKE 'pg_toast%';
SQL
)
[[ $table_count == 0 ]] || { echo 'Target database is not empty; no data overwritten.' >&2; exit 1; }
echo 'Restoring verified dump in one transaction'
if ! "${compose[@]}" exec -T postgres sh -ec 'exec pg_restore -U "$POSTGRES_USER" -d "$POSTGRES_DB" --no-owner --no-acl --single-transaction --exit-on-error' <"$dump_file" >/dev/null 2>&1; then
  echo 'Restore failed; transaction rolled back. No application started.' >&2; exit 1
fi
counts=$(query <<'SQL'
SELECT (SELECT count(*) FROM users), (SELECT count(*) FROM applications), (SELECT count(*) FROM application_status_history);
SQL
)
[[ $counts == '10|273|479' ]] || { echo 'Unexpected record counts; imported data retained for inspection. Application startup not enabled.' >&2; exit 1; }
revision=$(query <<'SQL'
SELECT version_num FROM alembic_version;
SQL
)
[[ $revision == 47448bcc7f4c ]] || { echo 'Unexpected migration revision; application startup not enabled.' >&2; exit 1; }
umask 077
printf 'sha256=%s\ncounts=%s\nalembic=%s\n' "$expected_sha256" "$counts" "$revision" >"$state_dir/database-restored"
echo 'Restored: users=10, applications=273, history=479, Alembic=47448bcc7f4c. Application has not been started.'
