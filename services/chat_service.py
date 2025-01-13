from models.chat import Chat
from models.user import User
from core.database import DatabaseManager
from core.redis_cache import RedisCache
from datetime import datetime
import uuid
import logging

class ChatService:
    def __init__(self, db: DatabaseManager, cache: RedisCache):
        self.db = db
        self.cache = cache

    async def create_chat(self, user1_id: str, user2_id: str) -> Chat:
        chat_id = str(uuid.uuid4())
        chat = Chat(
            id=chat_id,
            user1_id=user1_id,
            user2_id=user2_id,
            created_at=datetime.utcnow()
        )
        await self.db.save_chat(chat)
        await self.cache.set(f"chat:{chat_id}", chat.to_dict())
        return chat

    async def get_chat(self, chat_id: str) -> Chat:
        cached_chat = await self.cache.get(f"chat:{chat_id}")
        if cached_chat:
            return Chat.from_dict(cached_chat)

        chat = await self.db.get_chat(chat_id)
        if chat:
            await self.cache.set(f"chat:{chat_id}", chat.to_dict())
        return chat

    async def end_chat(self, chat_id: str):
        chat = await self.get_chat(chat_id)
        if chat:
            await self.db.delete_chat(chat_id)
            await self.cache.delete(f"chat:{chat_id}")
            return True
        return False

    async def update_message_map(self, chat_id: str, from_id: int, to_id: int):
        chat = await self.get_chat(chat_id)
        if chat:
            chat.message_map[str(from_id)] = to_id
            await self.db.save_chat(chat)
            await self.cache.set(f"chat:{chat_id}", chat.to_dict())