from datetime import datetime

from pydantic import BaseModel, Field, field_validator

from app.db.models import ApplicationStatus

# User schemas


class UserBase(BaseModel):
    login: str


class UserCreate(UserBase):
    password: str

    @field_validator("password")
    def validate_password(cls, v):
        message = ""
        if len(v) < 8:
            message += "Пароль должен содержать минимум 8 символов. "
        if not any(char.islower() for char in v):
            message += "Пароль должен содержать хотя бы одну строчную букву. "
        if not any(char.isupper() for char in v):
            message += "Пароль должен содержать хотя бы одну заглавную букву. "
        if not any(char.isdigit() for char in v):
            message += "Пароль должен содержать хотя бы одну цифру. "
        if not v.isascii():
            message += "Пароль должен содержать только латинские буквы. "
        if message:
            message = message.strip()
            raise ValueError(message)
        return v


class UserLogin(UserBase):
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


class ApplicationResponse(BaseModel):
    id: int
    user_id: int
    status: ApplicationStatus
    company_name: str
    contacts: str | None = None
    comments: str | None = None
    vacancy_url: str | None = None
    created_at: datetime
    updated_at: datetime
    days_since_creation: int

    class Config:
        from_attributes = True


class ApplicationCreate(BaseModel):
    company_name: str = Field(..., min_length=1, max_length=255)
    contacts: str | None = None
    comments: str | None = None
    vacancy_url: str | None = None


class ApplicationUpdate(ApplicationCreate):
    company_name: str | None = Field(None, min_length=1, max_length=255)
    status: ApplicationStatus | None = None
