from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from app.auth import get_current_user
from app.config import config as cf
from app.db.models import User

router = APIRouter(tags=["admin"])
templates = Jinja2Templates(directory="app/templates")


@router.get("/admin", response_class=HTMLResponse)
async def admin_page(request: Request, current_user: User = Depends(get_current_user)):
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Доступ запрещён")
    return templates.TemplateResponse(
        name="admin.html",
        context={
            "request": request,
            "smartcaptcha_site_key": cf.SMARTCAPTCHA_SITE_KEY,
        },
        request=request,
    )
