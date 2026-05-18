from fastapi import APIRouter, Depends, status

from app.auth import get_current_user
from app.crud import (
    create_application,
    delete_application,
    delete_status_history_entry,
    get_application,
    get_application_status_history,
    get_applications,
    update_application,
)
from app.db.database import SessionDep
from app.db.models import User
from app.schemas import (
    ApplicationCreate,
    ApplicationResponse,
    ApplicationStatusHistoryResponse,
    ApplicationUpdate,
)

router = APIRouter(prefix="/api/applications", tags=["applications"])


@router.get("", response_model=list[ApplicationResponse])
async def get_applications_endpoint(
    db: SessionDep, reverse: bool = False, current_user: User = Depends(get_current_user)
):
    """
    Get all applications for current user.
    """
    applications = await get_applications(db, reverse, current_user)
    return applications


@router.get("/{application_id}", response_model=ApplicationResponse)
async def get_application_endpoint(
    application_id: int, db: SessionDep, current_user: User = Depends(get_current_user)
):
    """
    Get application by id. Check if current user is the owner.
    """
    application = await get_application(application_id, db, current_user)
    return application


@router.post("", response_model=ApplicationResponse, status_code=status.HTTP_201_CREATED)
async def create_application_endpoint(
    app_data: ApplicationCreate, db: SessionDep, current_user: User = Depends(get_current_user)
):
    """
    Create application.
    """
    application = await create_application(app_data, db, current_user)
    return application


@router.patch("/{application_id}", response_model=ApplicationResponse)
async def update_application_endpoint(
    application_id: int,
    new_app_data: ApplicationUpdate,
    db: SessionDep,
    current_user: User = Depends(get_current_user),
):
    """
    Update application.
    """
    application = await update_application(application_id, new_app_data, db, current_user)
    return application


@router.delete(
    "/{application_id}/history/{history_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_status_history_endpoint(
    application_id: int,
    history_id: int,
    db: SessionDep,
    current_user: User = Depends(get_current_user),
):
    """
    Delete a status history entry. Cannot delete the first or last entry.
    """
    await delete_status_history_entry(application_id, history_id, db, current_user)
    return None


@router.get("/{application_id}/history", response_model=list[ApplicationStatusHistoryResponse])
async def get_application_status_history_endpoint(
    application_id: int,
    db: SessionDep,
    current_user: User = Depends(get_current_user),
):
    """
    Get status history for an application.
    """
    history = await get_application_status_history(application_id, db, current_user)
    return history


@router.delete("/{application_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_application_endpoint(
    application_id: int, db: SessionDep, current_user: User = Depends(get_current_user)
):
    """
    Delete application. Check if current user is the owner.
    """
    await delete_application(application_id, db, current_user)
    return None
