from fastapi import APIRouter, HTTPException, Response, status
from fastapi.responses import JSONResponse
from sqlalchemy import select

from app.auth import authenticate_user, create_access_and_refresh_tokens, get_user_by_login
from app.crud import create_user
from app.db.database import SessionDep
from app.db.models import User
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


@router.get("/users", response_model=list[UserResponse])  # TODO: remove this endpoint
async def get_users(session: SessionDep):
    """
    Get all users (debug endpoint).
    """
    result = await session.execute(select(User))
    users = result.scalars().all()
    return users


@router.post("/login")
async def login(response: Response, user_data: UserCreate, session: SessionDep) -> JSONResponse:
    """
    Authenticate user and return access and refresh tokens.
    """
    authenticated_user: User = await authenticate_user(session, user_data.login, user_data.password)
    if not authenticated_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Incorrect login or password"
        )
    access_token, refresh_token = await create_access_and_refresh_tokens(authenticated_user.login)
    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "bearer",
        },
    )
