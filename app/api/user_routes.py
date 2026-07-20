from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response, status
from sqlalchemy import func, select

from app.auth import (
    delete_all_user_sessions_by_username,
    get_current_user,
    has_admin_privileges,
    is_superadmin,
)
from app.config import config as cf
from app.crud import delete_user, set_user_admin_status
from app.db.database import SessionDep
from app.db.models import User
from app.schemas import (
    AdminActionRequest,
    AdminUserResponse,
    CurrentUserResponse,
    PaginatedUsersResponse,
)

router = APIRouter(prefix="/api/users", tags=["users"])


@router.get("/health")
async def test_page():
    return {"status": "Ok!"}


@router.get("", response_model=PaginatedUsersResponse)
async def get_users(
    db: SessionDep,
    current_user: User = Depends(get_current_user),
    sort_by: str = Query("created_at", description="Field to sort by: login or created_at"),
    order: str = Query("desc", description="Sort order: asc or desc"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(cf.ADMIN_PAGE_SIZE, ge=1, le=100, description="Users per page"),
):
    """
    Get all users with pagination. For users with admin role only.
    Supports sorting by login, created_at, or is_admin in ascending or descending order.
    """
    if not has_admin_privileges(current_user):
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

    # Get total count
    total_result = await db.execute(select(func.count(User.id)))
    total = total_result.scalar_one()

    # Build query with sorting and pagination
    sort_column = getattr(User, sort_by)
    query = (
        select(User)
        .order_by(sort_column.asc() if order == "asc" else sort_column.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )

    result = await db.execute(query)
    users = result.scalars().all()

    total_pages = (total + page_size - 1) // page_size

    return PaginatedUsersResponse(
        items=users,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )


@router.get("/me", response_model=CurrentUserResponse)
async def get_current_user_info(current_user: User = Depends(get_current_user)):
    """
    Get current user info, including superadmin status.
    """
    return CurrentUserResponse(
        id=current_user.id,
        login=current_user.login,
        is_admin=current_user.is_admin,
        created_at=current_user.created_at,
        is_superadmin=is_superadmin(current_user),
    )


@router.delete("/me", status_code=status.HTTP_204_NO_CONTENT)
async def delete_current_user(
    request: Request,
    response: Response,
    db: SessionDep,
    current_user: User = Depends(get_current_user),
):
    """
    Delete current user. Superadmin cannot be deleted.
    """
    if is_superadmin(current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This user is protected and cannot be deleted",
        )

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
    Superadmin cannot be deleted.
    """
    if not has_admin_privileges(current_user):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not enough permissions")

    user = await db.scalar(select(User).where(User.id == user_id))
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    # Protect superadmin from deletion
    if is_superadmin(user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This user is protected and cannot be deleted",
        )

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


@router.patch("/{user_id}/admin", response_model=AdminUserResponse)
async def toggle_admin_status(
    user_id: int,
    body: AdminActionRequest,
    db: SessionDep,
    current_user: User = Depends(get_current_user),
):
    """
    Set or unset admin status for a user.
    Superadmin only. Superadmin can also manage their own admin status.
    """
    if not is_superadmin(current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions to manage admin status",
        )

    updated_user = await set_user_admin_status(db, user_id, body.is_admin)
    return updated_user
