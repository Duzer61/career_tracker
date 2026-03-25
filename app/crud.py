from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import get_password_hash
from app.db.models import User
from app.schemas import UserCreate

# User crud


async def get_user_by_login(session: AsyncSession, login: str) -> User | None:
    """
    Get user by login.
    """
    result = await session.execute(select(User).where(User.login == login))
    return result.scalar_one_or_none()


async def create_user(session: AsyncSession, user_data: UserCreate) -> User:
    """
    Create a new user.
    """
    try:
        hashed_password = get_password_hash(user_data.password)
        user = User(login=user_data.login, hashed_password=hashed_password)
        session.add(user)
        await session.commit()
        await session.refresh(user)
        return user
    except IntegrityError:
        await session.rollback()
        raise ValueError(f"User with login '{user_data.login}' already exists")
