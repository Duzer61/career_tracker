#!/usr/bin/env bash
# Review, then run manually with sudo. Never supplies or reads secret values.
set -euo pipefail
[[ $EUID == 0 ]] || { echo 'Run this installer with sudo in your terminal.' >&2; exit 1; }
[[ $# == 0 ]] || { echo 'No arguments accepted.' >&2; exit 2; }
source_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)
project_dir=/srv/projects/career_tracker
config_dir=/etc/career-tracker
state_dir=/var/lib/career-tracker
# Installation does not start containers or change existing volumes.
if id career-deploy >/dev/null 2>&1; then
  echo 'career-deploy already exists; inspect it before proceeding. No changes made.' >&2
  exit 1
fi
[[ ! -e "$config_dir" && ! -e /usr/local/sbin/career-tracker-deploy && ! -e /usr/local/sbin/career-deploy-entry && ! -e /usr/local/sbin/career-tracker-restore && ! -e /usr/local/sbin/career-tracker-authorize-key && ! -e /etc/sudoers.d/career-tracker-deploy ]] || { echo 'Existing deployment configuration found; no changes made.' >&2; exit 1; }
# Validate sudoers before installation.
sudoers_temp=$(mktemp)
trap 'unlink "$sudoers_temp"' EXIT
printf '%s\n' 'career-deploy ALL=(root) NOPASSWD: /usr/local/sbin/career-tracker-deploy *' >"$sudoers_temp"
visudo -cf "$sudoers_temp" >/dev/null
install -d -o root -g root -m 0755 "$config_dir"
install -d -o root -g root -m 0700 "$state_dir" "$state_dir/backups"
install -o root -g root -m 0644 "$source_dir/docker-compose-career-production.yml" "$config_dir/compose.yml"
install -o root -g root -m 0755 "$source_dir/scripts/deploy-entry.sh" /usr/local/sbin/career-deploy-entry
install -o root -g root -m 0755 "$source_dir/scripts/deploy-root.sh" /usr/local/sbin/career-tracker-deploy
install -o root -g root -m 0755 "$source_dir/scripts/restore-root.sh" /usr/local/sbin/career-tracker-restore
install -o root -g root -m 0755 "$source_dir/scripts/authorize-deploy-key.sh" /usr/local/sbin/career-tracker-authorize-key
useradd --system --create-home --home-dir /var/lib/career-deploy --shell /bin/sh career-deploy
chown root:root /var/lib/career-deploy
chmod 0755 /var/lib/career-deploy
install -d -o root -g root -m 0755 /var/lib/career-deploy/.ssh
install -o root -g root -m 0440 "$sudoers_temp" /etc/sudoers.d/career-tracker-deploy
install -d -o dan -g dan -m 0700 "$project_dir/restore"
echo 'Installed. No SSH key enabled, no containers started, no existing data deleted.'
echo 'Next: create the server .env locally, authorize the dedicated public key, then run sudo /usr/local/sbin/career-tracker-restore.'
