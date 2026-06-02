from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.db.models import ApplicationStatus

# User schemas


class UserBase(BaseModel):
    login: str


class UserCreate(UserBase):
    password: str

    @field_validator("password")
    @classmethod
    def validate_password(cls, v: str) -> str:
        rules = [
            (len(v) >= 8, "Пароль должен содержать минимум 8 символов."),
            (any(c.islower() for c in v), "Пароль должен содержать хотя бы одну строчную букву."),
            (any(c.isupper() for c in v), "Пароль должен содержать хотя бы одну заглавную букву."),
            (any(c.isdigit() for c in v), "Пароль должен содержать хотя бы одну цифру."),
            (v.isascii(), "Пароль должен содержать только символы ASCII."),
        ]

        errors = [msg for is_valid, msg in rules if not is_valid]
        if errors:
            raise ValueError(" ".join(errors))
        return v


class UserLogin(UserBase):
    password: str


class UserResponse(UserBase):
    id: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


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
    vacancy_name: str
    contacts: str | None = None
    comments: str | None = None
    vacancy_url: str | None = None
    created_at: datetime
    updated_at: datetime
    days_since_creation: int

    model_config = ConfigDict(from_attributes=True)


class ApplicationCreate(BaseModel):
    company_name: str = Field(..., min_length=1, max_length=255)
    vacancy_name: str = Field(..., min_length=1, max_length=255)
    contacts: str | None = Field(None, max_length=500)
    comments: str | None = None
    vacancy_url: str | None = Field(None, max_length=500)


class ApplicationStatusHistoryResponse(BaseModel):
    id: int
    status: ApplicationStatus
    changed_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ApplicationUpdate(ApplicationCreate):
    company_name: str | None = Field(None, min_length=1, max_length=255)
    vacancy_name: str | None = Field(None, min_length=1, max_length=255)
    contacts: str | None = Field(None, max_length=500)
    vacancy_url: str | None = Field(None, max_length=500)
    status: ApplicationStatus | None = None
