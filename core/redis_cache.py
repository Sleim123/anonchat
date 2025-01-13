import asyncio
import redis.asyncio as redis
import json
from config.settings import Config
import logging

class RedisCache:
    def __init__(self):
        self.redis = None

    async def connect(self):
        if self.redis is None:
            try:
                self.redis = redis.Redis.from_url(Config.REDIS_URI)
                # Проверка соединения
                await self.redis.ping()
                logging.info("Successfully connected to Redis")
            except Exception as e:
                logging.error(f"Failed to connect to Redis: {e}")
                raise

    async def close(self):
        try:
            if self.redis:
                await self.redis.close()
                logging.info("Redis connection closed successfully")
        except Exception as e:
            logging.error(f"Error closing Redis connection: {e}")

    async def get(self, key: str):
        if not self.redis:
            await self.connect()
        try:
            value = await self.redis.get(key)
            return json.loads(value) if value else None
        except Exception as e:
            logging.error(f"Redis get error: {e}")
            return None

    async def set(self, key: str, value: any, ttl: int = None):
        if not self.redis:
            await self.connect()
        try:
            await self.redis.set(
                key,
                json.dumps(value),
                ex=ttl or Config.CACHE_TTL
            )
        except Exception as e:
            logging.error(f"Redis set error: {e}")

    async def delete(self, key: str):
        if not self.redis:
            await self.connect()
        try:
            await self.redis.delete(key)
        except Exception as e:
            logging.error(f"Redis delete error: {e}")

    async def exists(self, key: str) -> bool:
        if not self.redis:
            await self.connect()
        try:
            return await self.redis.exists(key)
        except Exception as e:
            logging.error(f"Redis exists error: {e}")
            return False