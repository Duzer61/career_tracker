from fastapi import APIRouter
from sqlalchemy import select

from app.db.database import SessionDep
from app.db.models import User
from app.schemas import UserResponse

router = APIRouter(prefix="/api/users", tags=["users"])


@router.get("/health")
async def test_page():
    return {"status": "Ok!"}


@router.get("", response_model=list[UserResponse])  # TODO: remove this endpoint
async def get_users(session: SessionDep):
    """
    Get all users (debug endpoint).
    """
    result = await session.execute(select(User))
    users = result.scalars().all()
    return users
