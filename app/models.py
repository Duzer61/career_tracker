import enum
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import String

from app.utils import utc_now

Base = declarative_base()


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    login: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)

    cards: Mapped[list["Card"]] = relationship(back_populates="user")

    def __repr__(self):
        return f"<User(id={self.id}, login={self.login})>"


class CardStatus(str, enum.Enum):
    CREATED = "created"
    HR_INTERVIEW = "hr_interview"
    TECH_INTERVIEW = "tech_interview"
    DIRECTOR_INTERVIEW = "director_interview"
    OFFER = "offer"
    REJECTED = "rejected"
    ARCHIVED = "archived"


class Card(Base):
    __tablename__ = "cards"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    status: Mapped[CardStatus] = mapped_column(
        Enum(CardStatus), nullable=False, default=CardStatus.CREATED
    )
    company_name: Mapped[str] = mapped_column(String(255), nullable=False)
    contacts: Mapped[str] = mapped_column(String(500), nullable=True)
    comments: Mapped[str] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now, onupdate=utc_now)

    user: Mapped["User"] = relationship(back_populates="cards")

    @property
    def days_since_creation(self) -> int:
        """Количество дней с создания карточки"""
        return (utc_now() - self.created_at).days

    def __repr__(self):
        return f"<Card(id={self.id}, company={self.company_name}, status={self.status})>"
