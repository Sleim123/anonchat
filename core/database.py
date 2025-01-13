from motor.motor_asyncio import AsyncIOMotorClient
from config.settings import Config
from models.user import User
from models.chat import Chat
import logging

class DatabaseManager:
    def __init__(self):
        self.client = None
        self.db = None
        self.users = None
        self.chats = None
        self.blocked = None

    async def connect(self):
        try:
            self.client = AsyncIOMotorClient(Config.MONGODB_URI)
            self.db = self.client[Config.DATABASE_NAME]
            self.users = self.db.users
            self.chats = self.db.chats
            self.blocked = self.db.blocked
            
            # Create indexes
            await self.init_indexes()
            logging.info("Successfully connected to MongoDB")
        except Exception as e:
            logging.error(f"Failed to connect to MongoDB: {e}")
            raise

    async def close(self):
        """Закрытие соединения с базой данных"""
        try:
            if self.client:
                self.client.close()
                logging.info("Database connection closed successfully")
        except Exception as e:
            logging.error(f"Error closing database connection: {e}")

    async def init_indexes(self):
        await self.users.create_index("status")
        await self.users.create_index("interests")
        await self.users.create_index("last_activity")
        await self.chats.create_index([("user1_id", 1), ("user2_id", 1)])

    async def get_user(self, user_id: str) -> User:
        data = await self.users.find_one({"id": user_id})
        return User.from_dict(data) if data else None

    async def save_user(self, user: User):
        await self.users.update_one(
            {"id": user.id},
            {"$set": user.to_dict()},
            upsert=True
        )

    async def get_chat(self, chat_id: str) -> Chat:
        data = await self.chats.find_one({"id": chat_id})
        return Chat.from_dict(data) if data else None

    async def save_chat(self, chat: Chat):
        await self.chats.update_one(
            {"id": chat.id},
            {"$set": chat.to_dict()},
            upsert=True
        )

    async def delete_chat(self, chat_id: str):
        await self.chats.delete_one({"id": chat_id})

    async def get_matching_users(self, user: User, limit: int = 10):
        cursor = self.users.find({
            "status": "searching",
            "id": {"$ne": user.id},
            "interests": {"$in": user.interests} if user.interests else {"$exists": True}
        }).limit(limit)
        
        return [User.from_dict(doc) async for doc in cursor]

    async def is_blocked(self, user_id: str) -> bool:
        return bool(await self.blocked.find_one({"user_id": user_id}))

    async def block_user(self, user_id: str):
        await self.blocked.insert_one({"user_id": user_id})

    async def unblock_user(self, user_id: str):
        await self.blocked.delete_one({"user_id": user_id})