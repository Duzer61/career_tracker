# Career Tracker: AdminVPS

VPS: `155.212.246.84`, Ubuntu 26.04.1 LTS, project directory `/srv/projects/career_tracker`.

## Access model

- `dan` retains existing personal SSH and sudo access. No membership in `docker` is required.
- `career-deploy` has no Docker membership and no general sudo permission. Its SSH key is forced through `/usr/local/sbin/career-deploy-entry` with forwarding disabled.
- The only accepted command is `deploy sha256:<64 lowercase hex characters>`. The root-owned wrapper fixes the image repository to `duzer61/career_tracker`, the Compose path, the project name and the environment file.
- Root-owned configuration: `/etc/career-tracker/compose.yml`. CI never uploads scripts or Compose to the server. Infrastructure changes require an administrator to review and install the new configuration.
- `/var/lib/career-tracker` contains the restore marker, predeployment dumps and current deployed image. It is accessible only to root.
- The application is bound to `127.0.0.1:9500`. PostgreSQL and Redis have no published ports.

The deploy key can update application code and therefore access application data through that code. This scheme restricts direct host administration; it does not make an untrusted application image safe.

## First installation (manual administrator steps)

Review the supplied installer and root scripts, then on the VPS run:

```bash
sudo bash /srv/projects/career_tracker/bootstrap/scripts/install-adminvps.sh
```

The installer refuses to overwrite an existing deployment installation. It creates the restricted account and fixed scripts but does not start containers or enable an SSH key. It leaves the existing `/srv/projects/career_tracker/docker-compose-career-production.yml` untouched; the runtime uses the reviewed copy in `/etc/career-tracker`.

Create the environment file manually on the VPS; if one already exists, do not overwrite it:

```bash
cd /srv/projects/career_tracker
(umask 077; set -o noclobber; cat bootstrap/.env.example > .env)
nano .env
```

Replace the three `CHANGE_ME_...` values with three distinct new random hexadecimal secrets. Generate them in your own terminal, for example with `openssl rand -hex 32`; do not send them to chat. Hex values avoid the URL-encoding limitations of the existing database and Redis connection builders. Keep the file unquoted, with `KEY=value` lines. Do not reuse old infrastructure secrets after the incident.

`SUPERADMIN_LOGIN=Duzer` restores superadministrator rights through configuration. The allowlist currently prevents new registrations except `Duzer`; existing users can still log in. CAPTCHA keys are empty; set new provider keys locally if enabling CAPTCHA.

Do not run `cat .env`, `docker compose config` without `-q`, `docker inspect` on container environment, or paste raw application logs into chat.

## Restore before first application startup

The verified archive is uploaded to `/srv/projects/career_tracker/restore/career_db.dump`. Run:

```bash
sudo /usr/local/sbin/career-tracker-restore
```

The script checks the fixed SHA-256, starts only PostgreSQL, refuses a nonempty target, restores in one transaction and verifies 10 users, 273 applications, 479 history records and Alembic revision `47448bcc7f4c`. Only after success is the root-owned restore marker written. It does not start the application. Repeated import is refused.

Never use `down -v`, `pg_restore --clean`, database drops or volume cleanup to resolve an import issue without separately reviewing the existing data.

## Dedicated GitHub SSH key

In your own local terminal, create a new key for CI, without replacing an existing file:

```bash
test ! -e ~/.ssh/career_adminvps_actions && \
  ssh-keygen -t ed25519 -f ~/.ssh/career_adminvps_actions -N '' -C career-tracker-actions
scp ~/.ssh/career_adminvps_actions.pub dan@155.212.246.84:/srv/projects/career_tracker/restore/career-actions.pub
ssh -t dan@155.212.246.84 'sudo /usr/local/sbin/career-tracker-authorize-key'
```

Only the public `.pub` file is uploaded to the VPS. Privately place the private key in GitHub Actions secret `SSH_KEY`. The assistant must not read the private key. This CI key has no passphrase; the existing `SSH_PASSPHRASE` secret is not used by the new workflow.

The authorization command refuses an existing `authorized_keys` rather than replacing access. The dedicated account's home and authorized_keys are root-owned.

## GitHub Actions configuration

Repository: `Duzer61/career_tracker`. Configure secrets in **Settings → Secrets and variables → Actions** (repository scope, or the `production` environment where applicable):

| Secret | New value / purpose |
| --- | --- |
| `HOST` | `155.212.246.84` |
| `USER` | `career-deploy` |
| `SSH_KEY` | New dedicated private CI key; enter privately |
| `SSH_KNOWN_HOSTS` | Trusted public host-key record prepared in `deployment/SSH_KNOWN_HOSTS.txt` in the backup workspace; not a private key |
| `DOCKER_USERNAME` | Docker Hub account `duzer61` |
| `DOCKER_PASSWORD` | New Docker Hub access token with permission to publish `career_tracker`; enter privately |

Application database passwords, Redis password and signing key stay exclusively in the VPS `.env`; the workflow no longer needs their GitHub secrets. Keep old secrets until the new setup has been verified, then revoke obsolete credentials deliberately. Deleting a GitHub secret alone does not revoke a key or token at its issuer.

`production` may have required reviewers configured in GitHub. Check that stale environment-level secrets do not override the new repository-level values.

- `develop` and pull requests: tests only.
- `main`: tests, image build and push with commit SHA tag.
- Deployment additionally requires repository variable `CAREER_DEPLOY_ENABLED=true`. Leave it unset until restore and key setup have succeeded.
- Workflow deploys the exact digest returned by the build, not mutable `latest`.
- Actions are pinned to verified commit SHAs. Deploys are serialized and protected by a server-side lock.

The deployment checks the restore marker, saves a database dump, stops only this application during migrations, runs Alembic upgrade and checks heads, then starts the app and verifies health and localhost HTTP. Failures retain data and suppress raw output. Database rollback is never automatic; a failed migration/startup may leave the app stopped until an administrator investigates.

## First launch and checks

After restoration, a successful workflow build supplies the image digest. Either enable the repository variable and run the workflow on `main`, or an administrator can run the same reviewed command directly:

```bash
sudo /usr/local/sbin/career-tracker-deploy 'deploy sha256:REPLACE_WITH_ACTUAL_64_HEX_DIGEST'
```

The placeholder command intentionally fails validation until a real digest is supplied.

Inspect safe status locally on the VPS:

```bash
sudo docker ps --format 'table {{.Names}}\t{{.Status}}\t{{.Ports}}'
curl --fail --silent --output /dev/null --write-out '%{http_code}\n' http://127.0.0.1:9500/
```

For browser testing before Nginx setup, open a personal SSH tunnel:

```bash
ssh -N -L 9500:127.0.0.1:9500 dan@155.212.246.84
```

Then visit http://localhost:9500. Nginx and HTTPS are configured separately; no public application port is opened.

Predeployment dumps are retained under `/var/lib/career-tracker/backups`; no automatic data deletion or Docker pruning is performed. Monitor disk usage and agree a retention policy separately.

## Branch scope

This migration is prepared from `develop` at commit `1958cfc`. Application backup functionality is not included: there is no `/backups` mount, `pg_backups` volume or `BACKUP_*` configuration. The database dump before deployment is an infrastructure safeguard executed inside PostgreSQL, separately from the unfinished application backup feature.
