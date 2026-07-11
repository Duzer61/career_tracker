from datetime import datetime

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import get_current_user
from app.crud import get_statistics
from app.db.database import get_session as get_db
from app.db.models import User
from app.schemas import StatisticsSummary

router = APIRouter(prefix="/api/statistics", tags=["statistics"])


@router.get("", response_model=StatisticsSummary)
async def statistics(
    date_from: datetime | None = Query(
        default=None,
        description="Начало периода (по дате создания отклика)",
    ),
    date_to: datetime | None = Query(
        default=None,
        description="Конец периода (по дате создания отклика)",
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
    return await get_statistics(
        db=db,
        current_user=current_user,
        date_from=date_from,
        date_to=date_to,
    )
