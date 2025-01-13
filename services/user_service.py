from models.user import User
from core.database import DatabaseManager
from core.redis_cache import RedisCache
from datetime import datetime
import logging

class UserService:
    def __init__(self, db: DatabaseManager, cache: RedisCache):
        self.db = db
        self.cache = cache

    async def get_user(self, user_id: str) -> User:
        # Try to get from cache first
        cached_user = await self.cache.get(f"user:{user_id}")
        if cached_user:
            return User.from_dict(cached_user)

        # If not in cache, get from database
        user = await self.db.get_user(user_id)
        if user:
            await self.cache.set(f"user:{user_id}", user.to_dict())
        return user

    async def create_user(self, user_id: str) -> User:
        user = User(
            id=user_id,
            status="normal",
            last_activity=datetime.utcnow()
        )
        await self.db.save_user(user)
        await self.cache.set(f"user:{user_id}", user.to_dict())
        return user

    async def update_user(self, user: User):
        user.last_activity = datetime.utcnow()
        await self.db.save_user(user)
        await self.cache.set(f"user:{user.id}", user.to_dict())

    async def set_premium(self, user_id: str, premium: bool):
        user = await self.get_user(user_id)
        if user:
            user.premium = premium
            await self.update_user(user)
            return True
        return False

    async def update_user_status(self, user_id: str, status: str):
        user = await self.get_user(user_id)
        if user:
            user.status = status
            await self.update_user(user)
            return True
        return False

    async def increment_chat_count(self, user_id: str):
        user = await self.get_user(user_id)
        if user:
            user.chats_count += 1
            await self.update_user(user)