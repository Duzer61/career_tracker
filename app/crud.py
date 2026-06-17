from datetime import datetime, timedelta

from fastapi import HTTPException
from sqlalchemy import asc, desc, select
from sqlalchemy import update as sqlalchemy_update
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import get_password_hash
from app.db.models import Application, ApplicationStatus, ApplicationStatusHistory, User
from app.schemas import ApplicationCreate, ApplicationUpdate, UserCreate
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
