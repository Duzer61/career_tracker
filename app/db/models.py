import enum
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, Text
from sqlalchemy.orm import Mapped, declarative_base, mapped_column, relationship
from sqlalchemy.types import String

from app.utils import utc_now

Base = declarative_base()


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    login: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    is_admin: Mapped[bool] = mapped_column(default=False)

    applications: Mapped[list["Application"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )

    def __repr__(self):
        return f"<User(id={self.id}, login={self.login}, is_admin={self.is_admin})>"


class ApplicationStatus(str, enum.Enum):
    CREATED = "created"
    HR_INTERVIEW = "hr_interview"
    TECH_INTERVIEW = "tech_interview"
    OFFER = "offer"
    AUTO_REJECT = "auto_reject"
    REJECTED = "rejected"
    IGNORED = "ignored"


class Application(Base):
    __tablename__ = "applications"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    status: Mapped[ApplicationStatus] = mapped_column(
        Enum(ApplicationStatus), nullable=False, default=ApplicationStatus.CREATED
    )
    company_name: Mapped[str] = mapped_column(String(255), nullable=False)
    vacancy_name: Mapped[str] = mapped_column(String(255), nullable=False, default="Not specified")
    contacts: Mapped[str] = mapped_column(String(500), nullable=True)
    comments: Mapped[str] = mapped_column(Text, nullable=True)
    vacancy_url: Mapped[str] = mapped_column(String(500), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now, onupdate=utc_now)

    status_history: Mapped[list["ApplicationStatusHistory"]] = relationship(
        back_populates="application", cascade="all, delete-orphan"
    )

    user: Mapped["User"] = relationship(back_populates="applications")

    @property
    def days_since_creation(self) -> int:
        """Количество дней с создания карточки"""
        return (utc_now() - self.created_at).days

    def __repr__(self):
        return f"<Application(id={self.id}, company={self.company_name}, status={self.status})>"


class ApplicationStatusHistory(Base):
    __tablename__ = "application_status_history"

    id: Mapped[int] = mapped_column(primary_key=True)
    application_id: Mapped[int] = mapped_column(ForeignKey("applications.id"), nullable=False)
    status: Mapped[ApplicationStatus] = mapped_column(Enum(ApplicationStatus), nullable=False)
    changed_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=utc_now)

    application: Mapped["Application"] = relationship(back_populates="status_history")

    def __repr__(self):
        return (
            f"<ApplicationStatusHistory(id={self.id}, "
            f"application_id={self.application_id}, "
            f"status={self.status}, "
            f"changed_at={self.changed_at})>"
        )
