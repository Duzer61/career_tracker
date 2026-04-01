from fastapi import APIRouter, Depends, status

from app.auth import get_current_user
from app.crud import create_application_obj, get_applications_obj
from app.db.database import SessionDep
from app.db.models import User
from app.schemas import ApplicationCreate, ApplicationResponse

router = APIRouter(prefix="/api/applications", tags=["applications"])


@router.get("", response_model=list[ApplicationResponse])
async def get_applications(db: SessionDep, current_user: User = Depends(get_current_user)):
    """
    Get all applications for current user.
    """
    applications = await get_applications_obj(db, current_user)
    # application_responses = [ApplicationResponse.model_validate(application) for application in applications]
    return applications


@router.post("", response_model=ApplicationResponse, status_code=status.HTTP_201_CREATED)
async def create_application(
    app_data: ApplicationCreate, db: SessionDep, current_user: User = Depends(get_current_user)
):
    """
    Create application.
    """
    application = await create_application_obj(app_data, db, current_user)
    return application
