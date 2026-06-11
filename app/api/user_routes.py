from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response, status
from sqlalchemy import func, select

from app.auth import delete_all_user_sessions_by_username, get_current_user
from app.crud import delete_user
from app.db.database import SessionDep
from app.db.models import User
from app.schemas import AdminUserResponse

router = APIRouter(prefix="/api/users", tags=["users"])


@router.get("/health")
async def test_page():
    return {"status": "Ok!"}


@router.get("", response_model=list[AdminUserResponse])
async def get_users(
    db: SessionDep,
    current_user: User = Depends(get_current_user),
    sort_by: str = Query("created_at", description="Field to sort by: login or created_at"),
    order: str = Query("desc", description="Sort order: asc or desc"),
):
    """
    Get all users. For users with admin role only.
    Supports sorting by login or created_at in ascending or descending order.
    """
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="You can't use this endpoint"
        )

    # Validate sort_by and order
    valid_sort_fields = {"login", "created_at", "is_admin"}
    if sort_by not in valid_sort_fields:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid sort_by field. Must be one of: {', '.join(valid_sort_fields)}",
        )
    if order not in ("asc", "desc"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid order. Must be 'asc' or 'desc'",
        )

    # Build query with sorting
    sort_column = getattr(User, sort_by)
    query = select(User).order_by(sort_column.asc() if order == "asc" else sort_column.desc())

    result = await db.execute(query)
    users = result.scalars().all()
    return users


@router.get("/me", response_model=AdminUserResponse)
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
    await delete_all_user_sessions_by_username(current_user.login)
    # Delete cookies
    response.delete_cookie("access_token")
    response.delete_cookie("refresh_token")
    return None


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user_by_admin(
    user_id: int,
    db: SessionDep,
    current_user: User = Depends(get_current_user),
):
    """
    Delete user by ID. For admin users only.
    Prevents deleting the last admin user.
    """
    if not current_user.is_admin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not enough permissions")

    user = await db.scalar(select(User).where(User.id == user_id))
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    # Prevent deleting the last admin
    if user.is_admin:
        admin_count = await db.scalar(select(func.count(User.id)).where(User.is_admin.is_(True)))
        if admin_count <= 1:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Cannot delete the last admin user",
            )

    # Delete user from database
    await delete_user(db, user)
    # Delete all user sessions
    await delete_all_user_sessions_by_username(user.login)
    return None
