from fastapi import HTTPException, Request, status

from app.config import config as cf
from app.db.redis import redis_client


async def _check_rate_limit(key: str, max_attempts: int, window_seconds: int):
    """
    Enforce a sliding-window rate limit via Redis INCR + EXPIRE.
    """
    redis = await redis_client.get_client()
    current = await redis.incr(key)

    if current == 1:
        await redis.expire(key, window_seconds)

    if current > max_attempts:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many attempts. Please try again later.",
        )


async def rate_limit_login(
    request: Request,
    max_attempts: int = cf.MAX_LOGIN_ATTEMPTS,
    window_seconds: int = cf.WINDOW_LOGIN_ATTEMPTS,
):
    """
    Rate-limit login by client IP. Max attempts in time window.
    """
    client_ip = request.client.host if request.client else "unknown"
    key = f"rate_limit:login:ip:{client_ip}"
    await _check_rate_limit(key, max_attempts, window_seconds)
