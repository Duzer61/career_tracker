from typing import Annotated

import redis.asyncio as redis
from fastapi import Depends

from app.config import config as cf


class RedisClient:
    def __init__(self, url: str):
        self.url = url
        self.client: redis.Redis | None = None

    async def connect(self):
        """
        Redis async connection.
        """
        self.client = redis.from_url(
            self.url, decode_responses=True, encoding="utf-8"  # чтобы получать строки вместо байтов
        )
        # Проверка подключения
        try:
            await self.client.ping()
            print("✅ Подключено к Redis")
        except Exception as e:
            print(f"❌ Ошибка подключения к Redis: {e}")
            raise

    async def close(self):
        """
        Close Redis connection.
        """
        if self.client:
            await self.client.close()
            self.client = None
            print("🔌 Соединение с Redis закрыто")

    async def get_client(self) -> redis.Redis:
        """
        Get Redis client.
        """
        if not self.client:
            await self.connect()
        try:
            return self.client
        except Exception as e:
            print(f"Ошибка при работе с Redis: {e}")
            raise


# Создаём экземпляр клиента Redis
redis_client = RedisClient(cf.redis.redis_url)

RedisDep = Annotated[redis.Redis, Depends(redis_client.get_client)]
