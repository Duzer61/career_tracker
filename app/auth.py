import secrets
import uuid
from datetime import timedelta
from typing import Optional

from fastapi import Depends, HTTPException, Request, Response, status
from jose import jwt
from jose.exceptions import JWTError
from passlib.context import CryptContext
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import config as cf
from app.db.database import SessionDep
from app.db.models import User
from app.db.redis import redis_client
from app.utils import utc_now


def is_superadmin(user: User) -> bool:
    """Check if the user is a superadmin based on config."""
    return bool(cf.SUPERADMIN_LOGIN) and user.login == cf.SUPERADMIN_LOGIN


def has_admin_privileges(user: User) -> bool:
    """Check if the user has admin-level access (admin or superadmin)."""
    return user.is_admin or is_superadmin(user)


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


def create_jwt_token(payload: dict, expires_delta: Optional[timedelta] = None) -> str:
    """
    Create a JWT token.
    """
    to_encode = payload.copy()

    if expires_delta:
        expire = utc_now() + expires_delta
    else:
        expire = utc_now() + timedelta(minutes=cf.DEFAULT_TOKEN_LIFETIME)

    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, cf.SECRET_KEY, algorithm=cf.ALGORITHM)
    return encoded_jwt


async def create_access_and_refresh_tokens(
    username: str, session_id: str = None
) -> tuple[str, str]:
    """
    Create access and refresh tokens and store the refresh token in Redis,
    bound to the username, with TTL equal to REFRESH_TOKEN_EXP_DAYS.
    """
    # Generate session ID if not provided
    if session_id is None:
        session_id = str(uuid.uuid4())

    access_payload = {"sub": username, "token_type": "access", "sid": session_id}
    access_token_expires = timedelta(minutes=cf.ACCESS_TOKEN_EXP_MINUTES)
    access_token = create_jwt_token(access_payload, access_token_expires)

    refresh_payload = {"sub": username, "token_type": "refresh", "sid": session_id}
    refresh_token_expires = timedelta(days=cf.REFRESH_TOKEN_EXP_DAYS)
    refresh_token = create_jwt_token(refresh_payload, refresh_token_expires)

    redis = await redis_client.get_client()
    ttl = int(refresh_token_expires.total_seconds())  # TTL in seconds

    key = f"refresh_token:{username}:{session_id}"
    await redis.setex(key, ttl, refresh_token)

    # Save a list of active sessions for the user
    session_key = f"user_sessions:{username}"
    await redis.sadd(session_key, session_id)
    await redis.expire(session_key, ttl)

    return access_token, refresh_token


async def get_token_payload(token: str) -> dict:
    """
    Check if the token is valid, return payload.
    """
    try:
        payload: dict = jwt.decode(token, cf.SECRET_KEY, algorithms=[cf.ALGORITHM])
    except JWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid access token")
    return payload


async def check_and_get_refresh_token_payload(refresh_token: str) -> dict | None:
    """
    Check if the refresh token is valid, return payload or None.
    """
    payload = await get_token_payload(refresh_token)
    username = payload.get("sub")
    token_type = payload.get("token_type")
    session_id = payload.get("sid")

    if not username or not token_type or not session_id:
        return None
    if token_type != "refresh":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token type")
    # Check refresh token in Redis
    redis = await redis_client.get_client()
    key = f"refresh_token:{username}:{session_id}"
    stored_token = await redis.get(key)
    if not stored_token or not secrets.compare_digest(refresh_token, stored_token):
        return None
    return payload


async def refresh_tokens(refresh_token: str) -> dict:
    """
    Refresh access and refresh tokens.
    """
    payload = await check_and_get_refresh_token_payload(refresh_token)
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token"
        )
    username = payload.get("sub")
    session_id = payload.get("sid")
    new_access_token, new_refresh_token = await create_access_and_refresh_tokens(
        username, session_id
    )
    return new_access_token, new_refresh_token


async def get_current_username_with_session_id(request: Request) -> tuple[str, str]:
    """
    Get the current username from access token, validating session is still active.
    Return username and session ID.
    """
    access_token = request.cookies.get("access_token")
    if not access_token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")

    try:
        payload: dict = jwt.decode(access_token, cf.SECRET_KEY, algorithms=[cf.ALGORITHM])
        username = payload.get("sub")
        token_type = payload.get("token_type")
        session_id = payload.get("sid")

        if not username:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token: missing username"
            )
        if token_type != "access":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token type"
            )
        if not session_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token: missing session ID"
            )
        # Check if the session is still active
        redis = await redis_client.get_client()
        session_key = f"user_sessions:{username}"
        is_active = await redis.sismember(session_key, session_id)
        if not is_active:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Session has been revoked. Please login again.",
            )
        return username, session_id
    except JWTError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail=f"Invalid token: {str(e)}"
        )


async def get_current_user_with_session_id(request: Request, db: SessionDep) -> tuple[User, str]:
    """
    Get the current User from access token. Return User and session ID.
    """
    username, session_id = await get_current_username_with_session_id(request)
    # Get user from database
    user: User = await db.scalar(select(User).where(User.login == username))
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
    return user, session_id


async def get_current_user(
    user_with_session: tuple[User, str] = Depends(get_current_user_with_session_id),
) -> User:
    """
    Get the current user from access token.
    """
    return user_with_session[0]


async def delete_refresh_token_and_session_id(request: Request) -> None:
    """
    Delete refresh token and session ID for current user from Redis.
    """
    access_token = request.cookies.get("access_token")
    if not access_token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
    payload = await get_token_payload(access_token)
    username = payload.get("sub")
    session_id = payload.get("sid")
    if username and session_id:
        redis = await redis_client.get_client()
        # Delete refresh token
        key = f"refresh_token:{username}:{session_id}"
        await redis.delete(key)
        # Remove session ID from active sessions
        session_key = f"user_sessions:{username}"
        await redis.srem(session_key, session_id)


async def delete_all_user_sessions(request: Request) -> None:
    """
    Delete all refresh tokens and session IDs for a user from Redis.
    """
    access_token = request.cookies.get("access_token")
    if not access_token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
    payload = await get_token_payload(access_token)
    username = payload.get("sub")
    if username:
        await delete_all_user_sessions_by_username(username)


async def delete_all_user_sessions_except_current(username: str, current_session_id: str) -> None:
    """
    Delete all sessions for a user, except the one identified by current_session_id.
    Used when changing password — keeps the current device logged in.
    """
    redis = await redis_client.get_client()
    session_key = f"user_sessions:{username}"
    sessions = await redis.smembers(session_key)

    # Iterate over a copy to avoid "Set changed size during iteration"
    for session_id in list(sessions):
        if session_id == current_session_id:
            continue
        key = f"refresh_token:{username}:{session_id}"
        await redis.delete(key)
        await redis.srem(session_key, session_id)


async def delete_all_user_sessions_by_username(username: str) -> None:
    """
    Delete all refresh tokens and session IDs for a user by username.
    """
    redis = await redis_client.get_client()
    session_key = f"user_sessions:{username}"
    sessions = await redis.smembers(session_key)

    # Delete all refresh tokens
    for session_id in sessions:
        key = f"refresh_token:{username}:{session_id}"
        await redis.delete(key)
    # Remove all session IDs
    await redis.delete(session_key)


async def change_user_password(
    db: AsyncSession, user: User, new_password: str, current_session_id: str
) -> None:
    """
    Change user password, delete all remote sessions, keep current session alive.
    """
    user.hashed_password = get_password_hash(new_password)
    try:
        await db.commit()
    except SQLAlchemyError as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Ошибка при смене пароля: {e}",
        )
    # Revoke all other sessions so other devices must re-login
    await delete_all_user_sessions_except_current(user.login, current_session_id)


async def get_user_by_login(db: AsyncSession, login: str) -> User | None:
    """
    Get user by login from database.
    """
    result = await db.execute(select(User).where(User.login == login))
    return result.scalar_one_or_none()


async def authenticate_user(db: AsyncSession, username: str, password: str) -> User | None:
    """
    Authenticate a user by username and password. Return the user if authenticated, None otherwise.
    """
    user = await get_user_by_login(db, username)
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
        path="/",
    )
