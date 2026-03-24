from datetime import datetime

from pydantic import BaseModel

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
