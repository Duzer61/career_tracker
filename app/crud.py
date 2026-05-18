from fastapi import HTTPException
from sqlalchemy import asc, desc, select
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import get_password_hash
from app.db.models import Application, ApplicationStatus, ApplicationStatusHistory, User
from app.schemas import ApplicationCreate, ApplicationUpdate, UserCreate

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


async def delete_user(db: AsyncSession, current_user: User) -> None:  # TODO: Дописать
    """
    Delete a user.
    """
    try:
        await db.delete(current_user)
        await db.commit()
    except SQLAlchemyError as e:
        await db.rollback()
        raise ValueError(f"Error deleting user: {e}")


# Board, applications crud


async def get_applications(db: AsyncSession, reverse, current_user: User) -> list[Application]:
    """
    Return all applications for current user. Ordered by creation date. Descending.
    """
    result = await db.scalars(
        select(Application)
        .where(Application.user_id == current_user.id)
        .order_by(asc(Application.created_at) if reverse else desc(Application.created_at))
    )
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
