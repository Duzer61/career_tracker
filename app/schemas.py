from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.db.models import ApplicationStatus
from app.utils import validate_password_strength

# User schemas


class UserBase(BaseModel):
    login: str


class UserCreate(UserBase):
    password: str
    password_confirm: str
    captcha_token: str = ""

    @field_validator("password")
    @classmethod
    def validate_password(cls, v: str) -> str:
        return validate_password_strength(v)

    @model_validator(mode="after")
    def passwords_match(self) -> "UserCreate":
        if self.password != self.password_confirm:
            raise ValueError("Пароли не совпадают")
        return self


class UserLogin(UserBase):
    password: str
    captcha_token: str = ""


class UserResponse(UserBase):
    id: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class AdminUserResponse(UserResponse):
    is_admin: bool


class CurrentUserResponse(AdminUserResponse):
    is_superadmin: bool = False


class PaginatedUsersResponse(BaseModel):
    items: list[AdminUserResponse]
    total: int
    page: int
    page_size: int
    total_pages: int


class RefreshTokenSchema(BaseModel):
    refresh_token: str


class AccessTokenSchema(BaseModel):
    access_token: str


class AdminActionRequest(BaseModel):
    is_admin: bool


class PasswordChangeRequest(BaseModel):
    old_password: str
    new_password: str
    new_password_confirm: str

    @field_validator("new_password")
    @classmethod
    def validate_new_password(cls, v: str) -> str:
        return validate_password_strength(v)

    @model_validator(mode="after")
    def passwords_match(self) -> "PasswordChangeRequest":
        if self.new_password != self.new_password_confirm:
            raise ValueError("Новые пароли не совпадают")
        return self

    @model_validator(mode="after")
    def old_and_new_different(self) -> "PasswordChangeRequest":
        if self.old_password == self.new_password:
            raise ValueError("Новый пароль должен отличаться от старого")
        return self


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


# ─── Statistics schemas ───────────────────────────────────────────────────────


class FunnelStage(BaseModel):
    """Одна ступень воронки: статус, количество, конверсия."""

    status: ApplicationStatus
    status_label: str
    count: int
    pct_of_total: float
    pct_of_previous: float | None = None


class StageDuration(BaseModel):
    """Среднее время перехода между двумя статусами."""

    from_status: ApplicationStatus
    to_status: ApplicationStatus
    from_label: str
    to_label: str
    avg_hours: float
    median_hours: float
    min_hours: float
    max_hours: float


class StatisticsSummary(BaseModel):
    """Агрегированная статистика: воронка + время прохождения + общие метрики."""

    total_applications: int
    active_applications: int
    rejected_applications: int
    auto_rejected_applications: int
    ignored_applications: int
    offer_applications: int
    funnel: list[FunnelStage]
    time_to_stage: list[StageDuration]
