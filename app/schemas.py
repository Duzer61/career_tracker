from datetime import datetime

from pydantic import BaseModel

from app.db.models import Card

# User schemas


class UserBase(BaseModel):
    login: str


class UserCreate(UserBase):
    password: str


class UserResponse(UserBase):
    id: int
    created_at: datetime

    class Config:
        from_attributes = True


class AdminUserResponse(UserResponse):
    is_admin: bool


class RefreshTokenSchema(BaseModel):
    refresh_token: str


class AccessTokenSchema(BaseModel):
    access_token: str


class CardResponse(BaseModel):
    id: int
    user_id: int
    status: str
    company_name: str
    contacts: str | None
    comments: str | None
    created_at: datetime
    updated_at: datetime
    days_since_creation: int

    @classmethod
    def from_orm(cls, card: Card):
        return cls(
            id=card.id,
            user_id=card.user_id,
            status=card.status,
            company_name=card.company_name,
            contacts=card.contacts,
            comments=card.comments,
            created_at=card.created_at,
            updated_at=card.updated_at,
            days_since_creation=card.days_since_creation,
        )
