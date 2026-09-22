import asyncio
import os
import re
import subprocess
from datetime import datetime, timezone

from app.config import config as cf

# ─── Константы ───────────────────────────────────────────────────────────────
_BACKUP_PATTERN = re.compile(r"^backup_\d{8}_\d{6}\.dump$")


# ─── Вспомогательные функции ─────────────────────────────────────────────────
def human_size(num: int) -> str:
    """Convert a byte count to a human-readable string (e.g. 1.5 MB)."""
    if num < 0:
        raise ValueError("Размер не может быть отрицательным")
    if num < 1024:
        return f"{num} B"
    size = float(num)
    for unit in ("KB", "MB", "GB", "TB"):
        size /= 1024.0
        if size < 1024:
            return f"{size:.1f} {unit}"
    return f"{size:.1f} PB"


def _is_valid_backup_filename(filename: str) -> bool:
    """Check that the filename is a valid backup name (no path traversal)."""
    return bool(_BACKUP_PATTERN.match(filename))


def _backup_path(filename: str) -> str:
    """Return the full path for a backup filename inside BACKUP_DIR."""
    if not _is_valid_backup_filename(filename):
        raise ValueError("Недопустимое имя файла бэкапа")
    return os.path.join(cf.BACKUP_DIR, filename)


def _run_command(cmd: list[str], env_extra: dict[str, str] | None = None) -> None:
    """Run a subprocess command synchronously, raising ValueError on failure."""
    env = os.environ.copy()
    if env_extra:
        env.update(env_extra)
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            env=env,
            check=False,
            stdin=subprocess.DEVNULL,
        )
    except FileNotFoundError as exc:
        raise ValueError(
            "Утилита pg_dump не найдена. Проверьте установку postgresql-client"
        ) from exc
    if result.returncode != 0:
        stderr = result.stderr.strip() or "Неизвестная ошибка"
        raise ValueError(f"Ошибка выполнения команды: {stderr}")


# ─── Публичный API бэкапов ───────────────────────────────────────────────────
async def create_backup() -> dict:
    """Create a full database backup in custom pg_dump format.

    Returns a dict with backup metadata (filename, size, created_at).
    """
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    filename = f"backup_{timestamp}.dump"
    path = os.path.join(cf.BACKUP_DIR, filename)

    cmd = [
        "pg_dump",
        "-Fc",
        "-h",
        cf.POSTGRES_HOST,
        "-p",
        cf.POSTGRES_PORT,
        "-U",
        cf.POSTGRES_USER,
        "-f",
        path,
        cf.POSTGRES_DB,
    ]
    env_extra = {"PGPASSWORD": cf.POSTGRES_PASSWORD}

    await asyncio.to_thread(_run_command, cmd, env_extra)

    size = os.path.getsize(path)
    await cleanup_old_backups()
    return {
        "filename": filename,
        "size": size,
        "size_human": human_size(size),
        "created_at": datetime.now(timezone.utc).isoformat(),
    }


async def list_backups() -> list[dict]:
    """List all backup files in BACKUP_DIR, newest first."""
    backups: list[dict] = []

    def _scan() -> list[dict]:
        result: list[dict] = []
        if not os.path.isdir(cf.BACKUP_DIR):
            return result
        for name in os.listdir(cf.BACKUP_DIR):
            if not _is_valid_backup_filename(name):
                continue
            path = os.path.join(cf.BACKUP_DIR, name)
            stat = os.stat(path)
            result.append(
                {
                    "filename": name,
                    "size": stat.st_size,
                    "size_human": human_size(stat.st_size),
                    "created_at": datetime.fromtimestamp(
                        stat.st_mtime, tz=timezone.utc
                    ).isoformat(),
                }
            )
        result.sort(key=lambda b: b["created_at"], reverse=True)
        return result

    backups = await asyncio.to_thread(_scan)
    return backups


async def delete_backup(filename: str) -> None:
    """Delete a single backup file by its filename."""
    path = _backup_path(filename)

    def _remove() -> None:
        if not os.path.exists(path):
            raise ValueError("Бэкап не найден")
        os.remove(path)

    await asyncio.to_thread(_remove)


async def cleanup_old_backups() -> int:
    """Remove backup files older than BACKUP_RETENTION_DAYS. Returns count removed."""
    cutoff = datetime.now(timezone.utc).timestamp() - cf.BACKUP_RETENTION_DAYS * 86400
    removed = 0

    def _cleanup() -> int:
        count = 0
        if not os.path.isdir(cf.BACKUP_DIR):
            return count
        for name in os.listdir(cf.BACKUP_DIR):
            if not _is_valid_backup_filename(name):
                continue
            path = os.path.join(cf.BACKUP_DIR, name)
            try:
                if os.stat(path).st_mtime < cutoff:
                    os.remove(path)
                    count += 1
            except OSError, FileNotFoundError:
                continue
        return count

    removed = await asyncio.to_thread(_cleanup)
    return removed
