from datetime import timedelta
from typing import Optional

from jose import jwt
from passlib.context import CryptContext
from utils import utc_now

from app.config import config as cf

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verify a stored password against one provided by user.
    """
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """
    Generate a hashed password.
    """
    return pwd_context.hash(password)


def create_jwt_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """
    Create a JWT token.
    """
    to_encode = data.copy()

    if expires_delta:
        expire = utc_now() + expires_delta
    else:
        expire = utc_now() + timedelta(minutes=cf.DEFAULT_TOKEN_LIFETIME)

    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, cf.SECRET_KEY, algorithm=cf.ALGORITHM)
    return encoded_jwt


def create_access_and_refresh_tokens(username: str) -> str:
    """
    Create access and refresh tokens.
    """
    access_payload = {"sub": username, "token_type": "access"}
    access_token_expires = timedelta(minutes=cf.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_jwt_token(access_payload, access_token_expires)

    refresh_payload = {"sub": username, "token_type": "refresh"}
    refresh_token_expires = timedelta(days=cf.REFRESH_TOKEN_EXP_DAYS)
    refresh_token = create_jwt_token(refresh_payload, refresh_token_expires)

    return access_token, refresh_token
