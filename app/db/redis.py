from typing import Annotated, Awaitable, cast

import redis.asyncio as redis
from fastapi import Depends

from app.config import config as cf


class RedisClient:
    def __init__(self, url: str) -> None:
        self.url = url
        self.client: redis.Redis | None = None

    async def connect(self) -> redis.Redis:
        """
        Redis async connection.
        """
        if self.client is not None:
            return self.client
        client = redis.from_url(
            self.url, decode_responses=True, encoding="utf-8"  # чтобы получать строки вместо байтов
        )
        # Проверка подключения
        try:
            await cast(Awaitable[bool], client.ping())
            print("✅ Подключено к Redis")
        except Exception as e:
            print(f"❌ Ошибка подключения к Redis: {e}")
            raise
        self.client = client
        return client

    async def close(self) -> None:
        """
        Close Redis connection.
        """
        if self.client is not None:
            await self.client.close()
            self.client = None
            print("🔌 Соединение с Redis закрыто")

    async def get_client(self) -> redis.Redis:
        """
        Get Redis client.
        """
        client = self.client
        if client is None:
            try:
                client = await self.connect()
            except Exception as e:
                print(f"Ошибка при работе с Redis: {e}")
                raise
        return client


# Создаём экземпляр клиента Redis
redis_client = RedisClient(cf.redis.redis_url)

RedisDep = Annotated[redis.Redis, Depends(redis_client.get_client)]
