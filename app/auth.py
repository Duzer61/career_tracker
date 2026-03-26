import secrets
from datetime import timedelta
from typing import Optional

from fastapi import HTTPException, Response, status
from jose import jwt
from jose.exceptions import ExpiredSignatureError, JWTError
from passlib.context import CryptContext
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import config as cf
from app.db.models import User
from app.db.redis import redis_client
from app.schemas import AccessTokenSchema, RefreshTokenSchema
from app.utils import utc_now

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


async def create_access_and_refresh_tokens(username: str) -> tuple[str, str]:
    """
    Create access and refresh tokens and store the refresh token in Redis,
    bound to the username, with TTL equal to REFRESH_TOKEN_EXP_DAYS.
    """
    access_payload = {"sub": username, "token_type": "access"}
    access_token_expires = timedelta(minutes=cf.ACCESS_TOKEN_EXP_MINUTES)
    access_token = create_jwt_token(access_payload, access_token_expires)

    refresh_payload = {"sub": username, "token_type": "refresh"}
    refresh_token_expires = timedelta(days=cf.REFRESH_TOKEN_EXP_DAYS)
    refresh_token = create_jwt_token(refresh_payload, refresh_token_expires)

    redis = await redis_client.get_client()
    ttl = int(refresh_token_expires.total_seconds())  # TTL in seconds
    key = f"refresh_token:{username}"
    await redis.setex(key, ttl, refresh_token)

    return access_token, refresh_token


async def check_refresh_token(payload: dict, refresh_token: str) -> bool:
    """
    Check if the refresh token is valid.
    """
    if payload.get("token_type") != "refresh":
        return False
    username = payload.get("sub")
    if not username:
        return False
    redis = await redis_client.get_client()
    stored_token = await redis.get(f"refresh_token:{username}")
    if not stored_token:
        return False
    if not secrets.compare_digest(refresh_token, stored_token):
        return False
    return True


async def get_username_from_refresh_token(refresh_token: RefreshTokenSchema) -> Optional[str]:
    """
    Get the username from the refresh token. If the token is invalid, return None.
    """
    try:
        token = refresh_token.refresh_token
        payload: dict = jwt.decode(token, cf.SECRET_KEY, algorithms=[cf.ALGORITHM])
        if await check_refresh_token(payload, token):
            return payload.get("sub")
        else:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token"
            )
    except ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Refresh token expired"
        )
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token"
        )


def get_username_from_access_token(access_token: AccessTokenSchema) -> Optional[str]:
    pass


async def get_user_by_login(session: AsyncSession, login: str) -> User | None:
    """
    Get user by login.
    """
    result = await session.execute(select(User).where(User.login == login))
    return result.scalar_one_or_none()


async def authenticate_user(session: AsyncSession, username: str, password: str) -> User | None:
    """
    Authenticate a user by username and password. Return the user if authenticated, None otherwise.
    """
    user = await get_user_by_login(session, username)
    if not user:
        return None
    if not verify_password(password, user.hashed_password):
        return None
    return user


async def set_cookie(response: Response, access_token, refresh_token):
    """
    Set cookies for access and refresh tokens.
    """
    response.set_cookie(
        key="access_token",
        value=access_token,
        httponly=True,
        secure=cf.ENVIRON == "prod",
        samesite="lax",
        max_age=cf.ACCESS_TOKEN_EXP_MINUTES * 60,
        path="/",
    )

    response.set_cookie(
        key="refresh_token",
        value=refresh_token,
        httponly=True,
        secure=cf.ENVIRON == "prod",
        samesite="lax",
        max_age=cf.REFRESH_TOKEN_EXP_DAYS * 24 * 60 * 60,
        path="/api",
    )
