from sqlalchemy import select
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import get_password_hash
from app.db.models import Card, User
from app.schemas import UserCreate

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


# Board, cards crud


async def get_cards(db: AsyncSession, current_user: User) -> list[Card]:
    """
    Return all cards for current user.
    """
    result = await db.scalars(select(Card).where(Card.user_id == current_user.id))
    cards = result.all()
    return cards
