from collections import defaultdict
from datetime import datetime, timedelta

from fastapi import HTTPException
from sqlalchemy import asc, desc, func, select
from sqlalchemy import update as sqlalchemy_update
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import get_password_hash
from app.constants import FUNNEL_STATUSES, STATUS_LABELS, TERMINAL_STATUSES
from app.db.models import Application, ApplicationStatus, ApplicationStatusHistory, User
from app.schemas import (
    ApplicationCreate,
    ApplicationUpdate,
    FunnelStage,
    StageDuration,
    StatisticsSummary,
    UserCreate,
)
from app.statistics import compute_time_to_stage
from app.utils import start_of_day, utc_now

# User crud


async def create_user(db: AsyncSession, user_data: UserCreate) -> User:
    """
    Create a new user.
    """
    hashed_password = get_password_hash(user_data.password)
    user = User(login=user_data.login, hashed_password=hashed_password)
    db.add(user)
    try:
        await db.commit()
        await db.refresh(user)
        return user
    except IntegrityError:
        raise ValueError(f"User with login '{user_data.login}' already exists")


async def delete_user(db: AsyncSession, user: User) -> None:
    """
    Delete a user.
    """
    try:
        await db.delete(user)
        await db.commit()
    except SQLAlchemyError as e:
        await db.rollback()
        raise ValueError(f"Error deleting user: {e}")


async def set_user_admin_status(db: AsyncSession, user_id: int, is_admin: bool) -> User:
    """
    Set the admin status for a user.
    Returns the updated user.
    """
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    user.is_admin = is_admin
    try:
        await db.commit()
        await db.refresh(user)
        return user
    except SQLAlchemyError as e:
        await db.rollback()
        raise ValueError(f"Error updating admin status: {e}")


# Board, applications crud


async def get_applications(
    db: AsyncSession,
    reverse: bool,
    current_user: User,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
) -> list[Application]:
    """
    Return all applications for current user. Ordered by creation date. Descending.

    Parameters:
        date_from: filter applications created at or after this datetime.
        date_to: filter applications created at or before this datetime.
    """
    query = select(Application).where(Application.user_id == current_user.id)

    if date_from is not None:
        query = query.where(Application.created_at >= date_from)
    if date_to is not None:
        query = query.where(Application.created_at <= date_to)

    query = query.order_by(asc(Application.created_at) if reverse else desc(Application.created_at))

    result = await db.scalars(query)
    applications = result.all()
    return applications


async def create_application(
    app_data: ApplicationCreate, db: AsyncSession, current_user: User
) -> Application:
    """
    Create a new application.
    """
    app = Application(
        user_id=current_user.id,
        company_name=app_data.company_name,
        vacancy_name=app_data.vacancy_name,
        contacts=app_data.contacts,
        comments=app_data.comments,
        vacancy_url=app_data.vacancy_url,
    )
    db.add(app)
    try:
        await db.flush()
        history_entry = ApplicationStatusHistory(
            application_id=app.id, status=ApplicationStatus.CREATED
        )
        db.add(history_entry)
        await db.commit()
        await db.refresh(app)
        return app
    except IntegrityError as e:
        await db.rollback()
        raise ValueError(f"Database integrity error while creating application:: {e}")
    except SQLAlchemyError as e:
        await db.rollback()
        raise ValueError(f"Database error while creating application: {e}")


async def get_application(app_id: int, db: AsyncSession, current_user: User) -> Application:
    """
    Return application by id. Check if it belongs to current user.
    """
    application = await db.scalar(
        select(Application).where(Application.id == app_id, Application.user_id == current_user.id)
    )
    if not application:
        raise HTTPException(status_code=404, detail="Application not found")
    return application


async def update_application(
    app_id: int, new_app_data: ApplicationUpdate, db: AsyncSession, current_user: User
):
    """
    Update an application.
    """
    application = await get_application(app_id, db, current_user)
    update_data = new_app_data.model_dump(exclude_unset=True)

    old_status = application.status
    for key, value in update_data.items():
        setattr(application, key, value)

    new_status = application.status
    if "status" in update_data and old_status != new_status:
        history_entry = ApplicationStatusHistory(
            application_id=application.id,
            status=new_status,
        )
        db.add(history_entry)

    try:
        await db.commit()
        await db.refresh(application)
        return application
    except IntegrityError as e:
        await db.rollback()
        raise ValueError(f"Database integrity error while updating application:: {e}")
    except SQLAlchemyError as e:
        await db.rollback()
        raise ValueError(f"Error updating application: {e}")


async def get_application_status_history(
    app_id: int, db: AsyncSession, current_user: User
) -> list[ApplicationStatusHistory]:
    """
    Return status history for an application after verifying ownership.
    """
    application = await get_application(app_id, db, current_user)
    result = await db.scalars(
        select(ApplicationStatusHistory)
        .where(ApplicationStatusHistory.application_id == application.id)
        .order_by(asc(ApplicationStatusHistory.changed_at))
    )
    return result.all()


async def delete_status_history_entry(
    app_id: int, history_id: int, db: AsyncSession, current_user: User
) -> None:
    """
    Delete a status history entry.
    Rules:
    - First entry can never be deleted.
    - Last entry can be deleted only if there are exactly 2 entries
      AND both have the same status (i.e. they are duplicates).
    - Middle entries can be deleted freely.
    """
    application = await get_application(app_id, db, current_user)

    result = await db.scalars(
        select(ApplicationStatusHistory)
        .where(ApplicationStatusHistory.application_id == application.id)
        .order_by(asc(ApplicationStatusHistory.changed_at))
    )
    all_entries = result.all()

    if len(all_entries) < 2:
        raise HTTPException(
            status_code=409,
            detail="Cannot delete history entry: at least 2 entries are required",
        )
    first_id = all_entries[0].id
    last_id = all_entries[-1].id

    # Never allow deleting the first entry
    if history_id == first_id:
        raise HTTPException(
            status_code=409,
            detail="Cannot delete the first status history entry",
        )

    # Allow deleting the last entry only under specific conditions
    if history_id == last_id:
        if len(all_entries) > 2:
            raise HTTPException(
                status_code=409,
                detail="Cannot delete the last status history entry when there are more than 2 entries",
            )
        # Exactly 2 entries — allow only if statuses match
        if all_entries[0].status != all_entries[1].status:
            raise HTTPException(
                status_code=409,
                detail="Cannot delete the last status history entry: statuses of the two entries differ",
            )
        # Statuses match → fall through to deletion

    entry = await db.scalar(
        select(ApplicationStatusHistory).where(
            ApplicationStatusHistory.id == history_id,
            ApplicationStatusHistory.application_id == application.id,
        )
    )
    if not entry:
        raise HTTPException(status_code=404, detail="Status history entry not found")

    try:
        await db.delete(entry)
        await db.commit()
    except SQLAlchemyError as e:
        await db.rollback()
        raise ValueError(f"Error deleting status history entry: {e}")


async def auto_ignore_old_applications(db: AsyncSession, current_user: User, days: int) -> int:
    """
    Move all CREATED applications older than the specified number of days
    to IGNORED status for the current user.

    Uses bulk UPDATE and INSERT operations.
    Returns the number of affected applications.
    """
    cutoff_date = start_of_day(utc_now()) - timedelta(days=days)

    result = await db.scalars(
        select(Application.id).where(
            Application.user_id == current_user.id,
            Application.status == ApplicationStatus.CREATED,
            Application.created_at < cutoff_date,
        )
    )
    app_ids = result.all()

    if not app_ids:
        return 0

    now = utc_now()

    try:
        await db.execute(
            sqlalchemy_update(Application)
            .where(Application.id.in_(app_ids))
            .values(status=ApplicationStatus.IGNORED, updated_at=now)
        )

        history_values = [
            {
                "application_id": app_id,
                "status": ApplicationStatus.IGNORED,
                "changed_at": now,
            }
            for app_id in app_ids
        ]
        await db.execute(pg_insert(ApplicationStatusHistory), history_values)

        await db.commit()
    except SQLAlchemyError as e:
        await db.rollback()
        raise ValueError(f"Error auto-ignoring applications: {e}")

    return len(app_ids)


async def delete_application(application_id: int, db: AsyncSession, current_user: User) -> None:
    """
    Delete an application.
    """
    application = await get_application(application_id, db, current_user)
    try:
        await db.delete(application)
        await db.commit()
        return
    except SQLAlchemyError as e:
        await db.rollback()
        raise ValueError(f"Error deleting application: {e}")


# ─── Statistics ──────────────────────────────────────────────────────────────
# Приватные функции разбиты для читаемости; каждая отвечает за один аспект.


async def _get_general_metrics(
    db: AsyncSession,
    app_ids: list[int],
) -> tuple[int, int, int, int]:
    """
    Return (active, rejected, ignored, offer) counts based on current statuses.
    """
    status_counts: dict[ApplicationStatus, int] = defaultdict(int)
    rows = await db.execute(
        select(Application.status, func.count(Application.id))
        .where(Application.id.in_(app_ids))
        .group_by(Application.status)
    )
    for row in rows:
        status_counts[row[0]] = row[1]

    active = sum(
        count for status, count in status_counts.items() if status not in TERMINAL_STATUSES
    )
    rejected = status_counts.get(ApplicationStatus.REJECTED, 0) + status_counts.get(
        ApplicationStatus.AUTO_REJECT, 0
    )
    ignored = status_counts.get(ApplicationStatus.IGNORED, 0)
    offer = status_counts.get(ApplicationStatus.OFFER, 0)
    return active, rejected, ignored, offer


async def _build_funnel(
    db: AsyncSession,
    app_ids: list[int],
    total: int,
) -> list[FunnelStage]:
    """
    Count how many unique applications have ever reached each funnel status.
    Returns list ordered by FUNNEL_STATUSES with conversion percentages.
    """
    funnel_counts: dict[ApplicationStatus, int] = defaultdict(int)
    rows = await db.execute(
        select(
            ApplicationStatusHistory.status,
            func.count(func.distinct(ApplicationStatusHistory.application_id)),
        )
        .where(ApplicationStatusHistory.application_id.in_(app_ids))
        .group_by(ApplicationStatusHistory.status)
    )
    for row in rows:
        funnel_counts[row[0]] = row[1]

    funnel: list[FunnelStage] = []
    previous_count: int | None = None
    for fstatus in FUNNEL_STATUSES:
        count = funnel_counts.get(fstatus, 0)
        pct_of_total = round(count / total * 100, 1) if total > 0 else 0.0
        pct_of_previous: float | None = None
        if previous_count is not None and previous_count > 0:
            pct_of_previous = round(count / previous_count * 100, 1)
        funnel.append(
            FunnelStage(
                status=fstatus,
                status_label=STATUS_LABELS[fstatus],
                count=count,
                pct_of_total=pct_of_total,
                pct_of_previous=pct_of_previous,
            )
        )
        previous_count = count
    return funnel


async def _build_time_to_stage(
    db: AsyncSession,
    app_ids: list[int],
    total: int,
) -> list[StageDuration]:
    """
    Calculate average, median, min, max hours for each pipeline status transition.
    Uses CTE with LAG on first entry time per status per application.
    """
    status_pairs = list(zip(FUNNEL_STATUSES, FUNNEL_STATUSES[1:]))
    if not status_pairs or total == 0:
        return []

    first_times = (
        select(
            ApplicationStatusHistory.application_id,
            ApplicationStatusHistory.status,
            func.min(ApplicationStatusHistory.changed_at).label("first_at"),
        )
        .where(ApplicationStatusHistory.application_id.in_(app_ids))
        .group_by(
            ApplicationStatusHistory.application_id,
            ApplicationStatusHistory.status,
        )
        .cte("first_times")
    )

    with_lag = select(
        first_times.c.application_id,
        first_times.c.status,
        first_times.c.first_at,
        func.lag(first_times.c.first_at)
        .over(
            partition_by=first_times.c.application_id,
            order_by=first_times.c.first_at,
        )
        .label("prev_at"),
    ).cte("with_lag")

    rows = await db.execute(
        select(
            with_lag.c.status,
            with_lag.c.prev_at,
            with_lag.c.first_at,
        ).where(
            with_lag.c.status.in_(FUNNEL_STATUSES),
            with_lag.c.prev_at.isnot(None),
        )
    )

    raw_rows: list[tuple[ApplicationStatus, float, float]] = []
    for row in rows:
        to_status = ApplicationStatus(row[0])
        prev_at: datetime = row[1]
        first_at: datetime = row[2]
        raw_rows.append((to_status, prev_at.timestamp(), first_at.timestamp()))

    return compute_time_to_stage(raw_rows)


async def get_statistics(
    db: AsyncSession,
    current_user: User,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
) -> StatisticsSummary:
    """
    Build statistics summary for the current user:
    - funnel (conversion through pipeline statuses)
    - time to stage (average/median/min/max hours between status transitions)
    - general counts (total, active, rejected, ignored, offer)
    """
    # ── Subquery: application IDs for current user (with date filter) ──
    app_ids_query = select(Application.id).where(Application.user_id == current_user.id)
    if date_from is not None:
        app_ids_query = app_ids_query.where(Application.created_at >= date_from)
    if date_to is not None:
        app_ids_query = app_ids_query.where(Application.created_at <= date_to)

    result = await db.scalars(app_ids_query)
    app_ids = list(result.all())
    total = len(app_ids)

    if total == 0:
        return StatisticsSummary(
            total_applications=0,
            active_applications=0,
            rejected_applications=0,
            ignored_applications=0,
            offer_applications=0,
            funnel=[],
            time_to_stage=[],
        )

    active, rejected, ignored, offer = await _get_general_metrics(db, app_ids)
    funnel = await _build_funnel(db, app_ids, total)
    time_to_stage = await _build_time_to_stage(db, app_ids, total)

    return StatisticsSummary(
        total_applications=total,
        active_applications=active,
        rejected_applications=rejected,
        ignored_applications=ignored,
        offer_applications=offer,
        funnel=funnel,
        time_to_stage=time_to_stage,
    )
