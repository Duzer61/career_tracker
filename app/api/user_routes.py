from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy import select

from app.auth import delete_all_user_sessions, get_current_user
from app.crud import delete_user
from app.db.database import SessionDep
from app.db.models import User
from app.schemas import AdminUserResponse, UserResponse

router = APIRouter(prefix="/api/users", tags=["users"])


@router.get("/health")
async def test_page():
    return {"status": "Ok!"}


@router.get("", response_model=list[AdminUserResponse])  # TODO: remove this endpoint
async def get_users(db: SessionDep, current_user: User = Depends(get_current_user)):
    """
    Get all users. For users with admin role only.
    """
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="You can't use this endpoint"
        )
    result = await db.execute(select(User))
    users = result.scalars().all()
    return users


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(current_user: User = Depends(get_current_user)):
    """
    Get current user info.
    """
    return current_user


@router.delete("/me", status_code=status.HTTP_204_NO_CONTENT)
async def delete_current_user(
    request: Request,
    response: Response,
    db: SessionDep,
    current_user: User = Depends(get_current_user),
):
    """
    Delete current user.
    """
    # Delete user from database
    await delete_user(db, current_user)
    # Delete all user sessions
    await delete_all_user_sessions(request)
    # Delete cookies
    response.delete_cookie("access_token")
    response.delete_cookie("refresh_token")
    return None
