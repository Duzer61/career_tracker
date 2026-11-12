#!/bin/sh
# Installed root-owned; SSH always enters here, never an interactive shell.
exec /usr/bin/sudo -n /usr/local/sbin/career-tracker-deploy "${SSH_ORIGINAL_COMMAND:-}"
