from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import get_password_hash
from app.db.models import User
from app.schemas import UserCreate

# User crud


async def create_user(session: AsyncSession, user_data: UserCreate) -> User:
    """
    Create a new user.
    """
    hashed_password = get_password_hash(user_data.password)
    user = User(login=user_data.login, hashed_password=hashed_password)
    session.add(user)
    try:
        await session.commit()
        await session.refresh(user)
        return user
    except IntegrityError:
        raise ValueError(f"User with login '{user_data.login}' already exists")


async def delete_user(session: AsyncSession, current_user: User) -> None:  # TODO: Дописать
    """
    Delete a user.
    """
    try:
        await session.delete(current_user)
        await session.commit()
    except SQLAlchemyError as e:
        await session.rollback()
        raise ValueError(f"Error deleting user: {e}")
