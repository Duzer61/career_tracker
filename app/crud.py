from sqlalchemy import select
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import get_password_hash
from app.db.models import Application, User
from app.schemas import ApplicationCreate, UserCreate

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


async def get_applications_obj(db: AsyncSession, current_user: User) -> list[Application]:
    """
    Return all applications for current user.
    """
    result = await db.scalars(select(Application).where(Application.user_id == current_user.id))
    applications = result.all()
    return applications


async def create_application_obj(
    app_data: ApplicationCreate, db: AsyncSession, current_user: User
) -> Application:
    """
    Create a new application.
    """
    app = Application(
        user_id=current_user.id,
        company_name=app_data.company_name,
        contacts=app_data.contacts,
        comments=app_data.comments,
        vacancy_url=app_data.vacancy_url,
    )
    db.add(app)
    try:
        await db.commit()
        await db.refresh(app)
        return app
    except IntegrityError:
        raise ValueError("Error creating application")
