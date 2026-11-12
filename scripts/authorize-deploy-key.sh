#!/usr/bin/env bash
set -euo pipefail
[[ $EUID == 0 && $# == 0 ]] || { echo 'Run with sudo, without arguments.' >&2; exit 2; }
public_key=/srv/projects/career_tracker/restore/career-actions.pub
authorized_keys=/var/lib/career-deploy/.ssh/authorized_keys
[[ -f "$public_key" && ! -e "$authorized_keys" ]] || { echo 'Public key missing or authorized_keys already exists; stopped.' >&2; exit 1; }
[[ $(wc -l <"$public_key") == 1 ]] || { echo 'Expected one public key line.' >&2; exit 1; }
IFS=' ' read -r key_type key_blob key_comment <"$public_key"
[[ $key_type == ssh-ed25519 && $key_blob =~ ^[A-Za-z0-9+/=]+$ ]] || { echo 'Expected an Ed25519 public key.' >&2; exit 1; }
ssh-keygen -l -f "$public_key" >/dev/null
umask 022
printf 'restrict,command="/usr/local/sbin/career-deploy-entry" %s %s career-tracker-actions\n' "$key_type" "$key_blob" >"$authorized_keys"
chown root:root "$authorized_keys"
chmod 0644 "$authorized_keys"
echo 'Dedicated deploy key enabled with a forced command and forwarding disabled.'
