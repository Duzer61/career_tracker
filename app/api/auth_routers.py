from fastapi import APIRouter, HTTPException, Request, Response, status

from app.auth import (
    authenticate_user,
    create_access_and_refresh_tokens,
    delete_all_user_sessions,
    delete_refresh_token_and_session_id,
    get_user_by_login,
    refresh_tokens,
    set_cookie,
)
from app.crud import create_user
from app.db.database import SessionDep
from app.db.models import User
from app.schemas import UserCreate, UserResponse

router = APIRouter(prefix="/api/auth", tags=["authentication"])


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


@router.post("/login")
async def login(response: Response, user_data: UserCreate, session: SessionDep):
    """
    Authenticate user and return access and refresh tokens.
    """
    authenticated_user: User = await authenticate_user(session, user_data.login, user_data.password)
    if not authenticated_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Incorrect login or password"
        )
    access_token, refresh_token = await create_access_and_refresh_tokens(authenticated_user.login)
    await set_cookie(response, access_token, refresh_token)
    return {"message": "login successful"}


@router.post("/refresh")
async def refresh(request: Request, response: Response):
    """
    Refresh access and refresh tokens.
    """
    refresh_token = request.cookies.get("refresh_token")
    if not refresh_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Refresh token not found"
        )
    new_access_token, new_refresh_token = await refresh_tokens(refresh_token)
    await set_cookie(response, new_access_token, new_refresh_token)
    return {"message": "Tokens refreshed successfully"}


@router.post("/logout")
async def logout(request: Request, response: Response):
    """
    Logout current user session.
    """
    await delete_refresh_token_and_session_id(request)
    response.delete_cookie("access_token")
    response.delete_cookie("refresh_token")
    return {"message": "logout successful"}


@router.post("/logout-all")
async def logout_all_devises(request: Request, response: Response):
    """
    Logout all user sessions.
    """
    await delete_all_user_sessions(request)
    response.delete_cookie("access_token")
    response.delete_cookie("refresh_token")
    return {"message": "Logged out from all devices"}
