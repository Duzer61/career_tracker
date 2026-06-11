"""Pytest fixtures and configuration for Career Tracker tests."""

from typing import AsyncGenerator

import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from app.config import Config, DatabaseConfig, RedisConfig

TEST_DB_URL = "sqlite+aiosqlite:///:memory:"


def get_test_config() -> Config:
    return Config(
        db=DatabaseConfig(db_url=TEST_DB_URL),
        redis=RedisConfig(redis_url="redis://localhost:6379/0"),
        SECRET_KEY="test-secret-key-change-in-production",
        ALGORITHM="HS256",
        ACCESS_TOKEN_EXP_MINUTES=30,
        REFRESH_TOKEN_EXP_DAYS=7,
        ENVIRON="test",
        ONLY_ALLOWED_USERNAMES_MODE=False,
        ALLOWED_USERNAMES=[],
        IS_PROD=False,
        SMARTCAPTCHA_SITE_KEY="",
        SMARTCAPTCHA_SECRET_KEY="",
    )


# ──────────────────────────────────────────────
# Override config BEFORE any app imports
# ──────────────────────────────────────────────
# app/db/database.py creates engine at import time using cf.db.db_url,
# so we must set the test config before it is imported.
import app.config  # noqa: E402

app.config.config = get_test_config()

# ──────────────────────────────────────────────
# In-memory Redis mock
# ──────────────────────────────────────────────
# We replace the RedisClient class and the module-level singleton
# before main.py (or any router) imports them.
import app.db.redis  # noqa: E402


class InMemoryRedisMock:
    """A simple in-memory Redis-like store for testing."""

    def __init__(self):
        self._data: dict[str, str] = {}
        self._sets: dict[str, set[str]] = {}

    async def ping(self) -> bool:
        return True

    async def get(self, key: str) -> str | None:
        return self._data.get(key)

    async def setex(self, key: str, ttl: int, value: str) -> bool:
        self._data[key] = value
        return True

    async def delete(self, key: str) -> bool:
        self._data.pop(key, None)
        self._sets.pop(key, None)
        return True

    async def expire(self, key: str, ttl: int) -> bool:
        return True

    async def incr(self, key: str) -> int:
        current = int(self._data.get(key, 0))
        current += 1
        self._data[key] = str(current)
        return current

    async def sadd(self, key: str, value: str) -> bool:
        if key not in self._sets:
            self._sets[key] = set()
        self._sets[key].add(value)
        return True

    async def srem(self, key: str, value: str) -> bool:
        if key in self._sets:
            self._sets[key].discard(value)
        return True

    async def smembers(self, key: str) -> set[str]:
        return self._sets.get(key, set())

    async def sismember(self, key: str, value: str) -> bool:
        return value in self._sets.get(key, set())


class TestRedisClient:
    """Drop-in replacement for RedisClient that uses InMemoryRedisMock."""

    def __init__(self, url: str):
        self.url = url
        self._mock = InMemoryRedisMock()

    async def connect(self) -> None:
        pass

    async def close(self) -> None:
        pass

    async def get_client(self):
        return self._mock


# Replace the class and the module-level singleton so that every
# downstream import receives the test implementation.
app.db.redis.RedisClient = TestRedisClient
app.db.redis.redis_client = TestRedisClient(app.config.config.redis.redis_url)

# Now safe to import the FastAPI app
from main import app as fastapi_app  # noqa: E402

# Keep a reference to the mock for the reset fixture.
_test_redis_mock = app.db.redis.redis_client._mock

# ──────────────────────────────────────────────
# Override DB session dependency
# ──────────────────────────────────────────────

from app.db.database import get_session  # noqa: E402
from app.db.models import Base, User  # noqa: E402

test_engine = create_async_engine(TEST_DB_URL, echo=False)
TestSessionLocal = sessionmaker(test_engine, class_=AsyncSession, expire_on_commit=False)


@pytest_asyncio.fixture(autouse=True)
async def setup_database():
    """Create all tables before each test, drop after."""
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest_asyncio.fixture(autouse=True)
async def reset_redis():
    """Clear in-memory Redis mock between tests."""
    _test_redis_mock._data.clear()
    _test_redis_mock._sets.clear()
    yield


async def override_get_session() -> AsyncGenerator[AsyncSession, None]:
    async with TestSessionLocal() as session:
        yield session


fastapi_app.dependency_overrides[get_session] = override_get_session

# ──────────────────────────────────────────────
# Test fixtures
# ──────────────────────────────────────────────


@pytest_asyncio.fixture
async def test_session() -> AsyncGenerator[AsyncSession, None]:
    async with TestSessionLocal() as session:
        yield session


@pytest_asyncio.fixture
async def client() -> AsyncGenerator[AsyncClient, None]:
    transport = ASGITransport(app=fastapi_app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest_asyncio.fixture
async def test_user(test_session) -> User:
    from app.auth import get_password_hash

    user = User(login="testuser", hashed_password=get_password_hash("TestPass123"))
    test_session.add(user)
    await test_session.commit()
    await test_session.refresh(user)
    return user
