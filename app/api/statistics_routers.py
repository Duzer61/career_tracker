from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import get_current_user
from app.crud import get_statistics
from app.db.database import get_session as get_db
from app.db.models import User
from app.schemas import StatisticsSummary
from app.utils import end_of_day

router = APIRouter(prefix="/api/statistics", tags=["statistics"])
page_router = APIRouter(tags=["statistics_page"])
templates = Jinja2Templates(directory="app/templates")


@router.get("", response_model=StatisticsSummary)
async def statistics(
    date_from: str | None = Query(
        default=None,
        description="Начало периода в ISO-формате (например 2025-01-01)",
    ),
    date_to: str | None = Query(
        default=None,
        description="Конец периода в ISO-формате (например 2025-01-31)",
    ),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Return statistics summary for current user:
    - funnel — сколько уникальных откликов доходило до каждого статуса
    - time_to_stage — среднее/медианное/мин/макс время между статусами
    - общие счётчики (total, active, rejected, ignored, offer)
    """
    date_from_dt: datetime | None = None
    date_to_dt: datetime | None = None

    if date_from:
        try:
            date_from_dt = datetime.fromisoformat(date_from)
        except ValueError:
            raise HTTPException(
                status_code=422,
                detail=f"Неверный формат date_from: '{date_from}'. Используйте ISO-формат (напр. 2025-01-01)",
            )
        if date_from_dt.year < 2000 or date_from_dt.year > 2100:
            raise HTTPException(
                status_code=422,
                detail=f"Год в date_from должен быть от 2000 до 2100, получено: {date_from_dt.year}",
            )

    if date_to:
        try:
            date_to_dt = datetime.fromisoformat(date_to)
        except ValueError:
            raise HTTPException(
                status_code=422,
                detail=f"Неверный формат date_to: '{date_to}'. Используйте ISO-формат (напр. 2025-01-31)",
            )
        if date_to_dt.year < 2000 or date_to_dt.year > 2100:
            raise HTTPException(
                status_code=422,
                detail=f"Год в date_to должен быть от 2000 до 2100, получено: {date_to_dt.year}",
            )
        date_to_dt = end_of_day(date_to_dt)

    return await get_statistics(
        db=db,
        current_user=current_user,
        date_from=date_from_dt,
        date_to=date_to_dt,
    )


@page_router.get("/statistics", response_class=HTMLResponse)
async def statistics_page(request: Request):
    return templates.TemplateResponse(
        name="statistics.html",
        context={"request": request},
        request=request,
    )
