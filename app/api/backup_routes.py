from fastapi import Depends, HTTPException
from fastapi.responses import FileResponse

from app.api.admin_routes import router
from app.auth import get_current_user, has_admin_privileges
from app.backup import _is_valid_backup_filename, create_backup, delete_backup, list_backups
from app.config import config as cf
from app.db.models import User


def _require_admin(current_user: User) -> None:
    """Raise 403 unless the current user has admin privileges."""
    if not has_admin_privileges(current_user):
        raise HTTPException(status_code=403, detail="Доступ запрещён")


@router.get("/api/admin/backups")
async def get_backups(current_user: User = Depends(get_current_user)):
    _require_admin(current_user)
    try:
        backups = await list_backups()
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return {"backups": backups}


@router.post("/api/admin/backups")
async def create_new_backup(current_user: User = Depends(get_current_user)):
    _require_admin(current_user)
    try:
        backup = await create_backup()
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return backup


@router.get("/api/admin/backups/{filename}/download")
async def download_backup(filename: str, current_user: User = Depends(get_current_user)):
    _require_admin(current_user)
    if not _is_valid_backup_filename(filename):
        raise HTTPException(status_code=400, detail="Недопустимое имя файла бэкапа")
    path = f"{cf.BACKUP_DIR}/{filename}"
    return FileResponse(path, filename=filename, media_type="application/octet-stream")


@router.delete("/api/admin/backups/{filename}")
async def remove_backup(filename: str, current_user: User = Depends(get_current_user)):
    _require_admin(current_user)
    try:
        await delete_backup(filename)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return {"deleted": filename}
