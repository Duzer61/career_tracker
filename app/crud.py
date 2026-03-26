from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import get_password_hash
from app.db.models import User
from app.schemas import UserCreate

# User crud


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
