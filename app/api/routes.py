from fastapi import APIRouter, HTTPException, status

from app.crud import create_user, get_user_by_login
from app.db.database import SessionDep
from app.schemas import UserCreate, UserResponse

router = APIRouter(prefix="/api", tags=["api"])


@router.get("/test_page")
async def test_page():
    return {"message": "Hello World!"}


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register(user_data: UserCreate, session: SessionDep):
    """
    Register a new user.
    """
    db_user = await get_user_by_login(session, user_data.login)
    if db_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User with this login already exists",
        )
    user = await create_user(session, user_data)
    return user
