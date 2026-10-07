"""Tests for app/config.py load_config(), focusing on backup settings."""

import app.config as config_module
from app.config import load_config

REQUIRED_ENV = {
    "POSTGRES_HOST": "localhost",
    "POSTGRES_PORT": "5432",
    "POSTGRES_USER": "user",
    "POSTGRES_PASSWORD": "pass",
    "POSTGRES_DB": "db",
    "REDIS_PASSWORD": "redispass",
    "REDIS_HOST": "localhost",
    "REDIS_PORT": "6379",
    "SECRET_KEY": "secret",
    "ALGORITHM": "HS256",
    "ACCESS_TOKEN_EXP_MINUTES": "30",
    "REFRESH_TOKEN_EXP_DAYS": "7",
    "ENVIRON": "test",
}


def _set_required_env(monkeypatch) -> None:
    """Set all mandatory env vars and isolate from any local .env file."""
    for key, value in REQUIRED_ENV.items():
        monkeypatch.setenv(key, value)
    # Do not let a local .env leak into the test result.
    monkeypatch.setattr(config_module.Env, "read_env", lambda self: None)


def test_load_config_reads_backup_env(monkeypatch):
    """Backup settings must come from the environment when provided."""
    _set_required_env(monkeypatch)
    monkeypatch.setenv("BACKUP_DIR", "/custom/backups")
    monkeypatch.setenv("BACKUP_RETENTION_DAYS", "7")
    monkeypatch.setenv("BACKUP_TIMEOUT_SECONDS", "120")

    cfg = load_config()

    assert cfg.BACKUP_DIR == "/custom/backups"
    assert cfg.BACKUP_RETENTION_DAYS == 7
    assert cfg.BACKUP_TIMEOUT_SECONDS == 120


def test_load_config_backup_defaults(monkeypatch):
    """Backup settings fall back to defaults when env vars are absent."""
    _set_required_env(monkeypatch)
    monkeypatch.delenv("BACKUP_DIR", raising=False)
    monkeypatch.delenv("BACKUP_RETENTION_DAYS", raising=False)
    monkeypatch.delenv("BACKUP_TIMEOUT_SECONDS", raising=False)

    cfg = load_config()

    assert cfg.BACKUP_DIR == "/backups"
    assert cfg.BACKUP_RETENTION_DAYS == 30
    assert cfg.BACKUP_TIMEOUT_SECONDS == 600
