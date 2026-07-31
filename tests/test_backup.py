"""Tests for backup functionality (app/backup.py and app/api/backup_routes.py)."""

import os
from datetime import datetime, timedelta, timezone

import pytest

from app.backup import (
    _is_valid_backup_filename,
    cleanup_old_backups,
    create_backup,
    delete_backup,
    human_size,
    list_backups,
)
from app.config import config as cf
from tests.helpers import set_client_cookies

REGISTER_URL = "/api/auth/register"
LOGIN_URL = "/api/auth/login"
BACKUP_API = "/api/admin/backups"


def _make_backup_file(directory: str, filename: str, mtime=None) -> str:
    """Create a fake backup file on disk and return its full path."""
    path = os.path.join(directory, filename)
    with open(path, "wb") as f:
        f.write(b"fake dump content")
    if mtime is not None:
        os.utime(path, (mtime, mtime))
    return path


async def _register_and_login(client, login: str, password: str = "StrongPass1"):
    """Register a user and set client cookies."""
    await client.post(
        REGISTER_URL,
        json={"login": login, "password": password, "password_confirm": password},
    )
    resp = await client.post(LOGIN_URL, json={"login": login, "password": password})
    set_client_cookies(client, resp)


# ──────────────────────────────────────────────
# Unit tests: validation helpers
# ──────────────────────────────────────────────


class TestBackupFilenameValidation:
    def test_valid_name(self):
        assert _is_valid_backup_filename("backup_20250101_120000.dump") is True

    def test_rejects_path_traversal(self):
        assert _is_valid_backup_filename("../backup_20250101_120000.dump") is False
        assert _is_valid_backup_filename("/etc/passwd") is False
        assert _is_valid_backup_filename("backup_20250101_120000.dump/../../x") is False

    def test_rejects_wrong_format(self):
        assert _is_valid_backup_filename("backup_20250101_120000.sql") is False
        assert _is_valid_backup_filename("backup_20250101.dump") is False
        assert _is_valid_backup_filename("notes.txt") is False

    def test_human_size(self):
        assert human_size(0) == "0 B"
        assert human_size(1024) == "1.0 KB"
        assert human_size(1536) == "1.5 KB"
        assert human_size(1024 * 1024) == "1.0 MB"


# ──────────────────────────────────────────────
# Unit tests: backup directory operations
# ──────────────────────────────────────────────


@pytest.fixture
def backup_dir(tmp_path, monkeypatch):
    """Point BACKUP_DIR at a temp directory for the duration of a test."""
    monkeypatch.setattr(cf, "BACKUP_DIR", str(tmp_path))
    monkeypatch.setattr(cf, "BACKUP_RETENTION_DAYS", 7)
    return str(tmp_path)


class TestListAndDelete:
    async def test_list_backups_empty(self, backup_dir):
        backups = await list_backups()
        assert backups == []

    async def test_list_backups_returns_files_sorted(self, backup_dir):
        older = datetime.now(timezone.utc) - timedelta(days=2)
        _make_backup_file(backup_dir, "backup_20250101_100000.dump")
        _make_backup_file(backup_dir, "backup_20250102_100000.dump", mtime=older.timestamp())
        # Non-backup files should be ignored
        _make_backup_file(backup_dir, "notes.txt")

        backups = await list_backups()
        names = [b["filename"] for b in backups]
        assert "backup_20250102_100000.dump" in names
        assert "backup_20250101_100000.dump" in names
        assert "notes.txt" not in names
        # Newest first
        assert names[0] == "backup_20250101_100000.dump"
        assert all(b["size"] > 0 for b in backups)
        assert all(b["size_human"] for b in backups)
        assert all(b["created_at"] for b in backups)

    async def test_delete_backup_removes_file(self, backup_dir):
        path = _make_backup_file(backup_dir, "backup_20250101_100000.dump")
        await delete_backup("backup_20250101_100000.dump")
        assert not os.path.exists(path)

    async def test_delete_missing_backup_raises(self, backup_dir):
        with pytest.raises(ValueError):
            await delete_backup("backup_20250101_100000.dump")

    async def test_delete_invalid_name_raises(self, backup_dir):
        with pytest.raises(ValueError):
            await delete_backup("../etc/passwd")


class TestCleanupOldBackups:
    async def test_cleanup_removes_old_files(self, backup_dir):
        old = datetime.now(timezone.utc) - timedelta(days=30)
        new = datetime.now(timezone.utc)
        _make_backup_file(backup_dir, "backup_20250101_100000.dump", mtime=old.timestamp())
        _make_backup_file(backup_dir, "backup_20250102_100000.dump", mtime=new.timestamp())

        removed = await cleanup_old_backups()

        assert removed == 1
        remaining = [b["filename"] for b in await list_backups()]
        assert "backup_20250101_100000.dump" not in remaining
        assert "backup_20250102_100000.dump" in remaining

    async def test_cleanup_keeps_recent_files(self, backup_dir):
        recent = datetime.now(timezone.utc) - timedelta(days=1)
        _make_backup_file(backup_dir, "backup_20250101_100000.dump", mtime=recent.timestamp())

        removed = await cleanup_old_backups()

        assert removed == 0


# ──────────────────────────────────────────────
# Endpoint tests (admin-only)
# ──────────────────────────────────────────────


class TestBackupEndpoints:
    async def test_backups_require_auth(self, client):
        response = await client.get(BACKUP_API)
        assert response.status_code == 401

    async def test_regular_user_gets_403(self, client):
        await _register_and_login(client, "regularuser")
        response = await client.get(BACKUP_API)
        assert response.status_code == 403

    async def test_admin_can_list_backups(self, client, test_session, backup_dir):
        _make_backup_file(backup_dir, "backup_20250102_100000.dump")

        await _register_and_login(client, "backupadmin")
        # Simple fetch via SQLAlchemy to set admin flag
        from sqlalchemy import select

        from app.db.models import User

        result = await test_session.scalars(select(User).where(User.login == "backupadmin"))
        admin = result.one()
        admin.is_admin = True
        await test_session.commit()

        response = await client.get(BACKUP_API)
        assert response.status_code == 200
        data = response.json()
        assert len(data["backups"]) == 1
        assert data["backups"][0]["filename"] == "backup_20250102_100000.dump"

    async def test_create_backup_creates_file(self, client, test_session, backup_dir, monkeypatch):
        """create_backup() should produce a backup file when pg_dump succeeds."""
        import app.backup as backup_module

        def _fake_run_command(cmd, env_extra=None):
            # Find the "-f <path>" argument and create an empty dump file.
            for i, arg in enumerate(cmd):
                if arg == "-f":
                    with open(cmd[i + 1], "wb") as f:
                        f.write(b"fake dump")
                    return

        monkeypatch.setattr(backup_module, "_run_command", _fake_run_command)

        await _register_and_login(client, "backupadmin")
        from sqlalchemy import select

        from app.db.models import User

        result = await test_session.scalars(select(User).where(User.login == "backupadmin"))
        admin = result.one()
        admin.is_admin = True
        await test_session.commit()

        created = await create_backup()
        assert "filename" in created
        assert created["filename"].endswith(".dump")
        assert created["size"] == len(b"fake dump")

        backups = await list_backups()
        assert len(backups) == 1
        assert backups[0]["filename"] == created["filename"]

    async def test_delete_backend_endpoint(self, client, test_session, backup_dir):
        _make_backup_file(backup_dir, "backup_20250102_100000.dump")

        await _register_and_login(client, "backupadmin")
        from sqlalchemy import select

        from app.db.models import User

        result = await test_session.scalars(select(User).where(User.login == "backupadmin"))
        admin = result.one()
        admin.is_admin = True
        await test_session.commit()

        response = await client.delete(f"{BACKUP_API}/backup_20250102_100000.dump")
        assert response.status_code == 200
        assert response.json() == {"deleted": "backup_20250102_100000.dump"}
        remaining = await list_backups()
        assert remaining == []

    async def test_download_backend_endpoint(self, client, test_session, backup_dir):
        _make_backup_file(backup_dir, "backup_20250102_100000.dump")

        await _register_and_login(client, "backupadmin")
        from sqlalchemy import select

        from app.db.models import User

        result = await test_session.scalars(select(User).where(User.login == "backupadmin"))
        admin = result.one()
        admin.is_admin = True
        await test_session.commit()

        response = await client.get(f"{BACKUP_API}/backup_20250102_100000.dump/download")
        assert response.status_code == 200
        assert response.content == b"fake dump content"

    async def test_download_invalid_name_returns_400(self, client, test_session, backup_dir):
        await _register_and_login(client, "backupadmin")
        from sqlalchemy import select

        from app.db.models import User

        result = await test_session.scalars(select(User).where(User.login == "backupadmin"))
        admin = result.one()
        admin.is_admin = True
        await test_session.commit()

        response = await client.get(f"{BACKUP_API}/..%2Fetc%2Fpasswd/download")
        assert response.status_code in (400, 404)

    async def test_delete_invalid_name_returns_400(self, client, test_session, backup_dir):
        await _register_and_login(client, "backupadmin")
        from sqlalchemy import select

        from app.db.models import User

        result = await test_session.scalars(select(User).where(User.login == "backupadmin"))
        admin = result.one()
        admin.is_admin = True
        await test_session.commit()

        response = await client.delete(f"{BACKUP_API}/..%2Fetc%2Fpasswd")
        assert response.status_code in (400, 404)
