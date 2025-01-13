from models.user import User
from core.database import DatabaseManager
from datetime import datetime, timedelta
import logging

class MatchingService:
    def __init__(self, db: DatabaseManager):
        self.db = db

    async def find_match(self, user: User) -> User:
        query = {
            "status": "searching",
            "id": {"$ne": user.id},
            "last_activity": {
                "$gt": datetime.utcnow() - timedelta(minutes=5)
            }
        }

        # Add gender preferences if specified
        if user.gender and hasattr(user, 'search_gender'):
            query["gender"] = user.search_gender

        # Add interests matching if user has interests
        if user.interests:
            query["interests"] = {"$in": user.interests}

        # Find matching user
        matching_user = await self.db.users.find_one(query)
        return User.from_dict(matching_user) if matching_user else None

    async def are_users_blocked(self, user1_id: str, user2_id: str) -> bool:
        block_key = ",".join(sorted([user1_id, user2_id]))
        block_data = await self.db.blocked.find_one({"pair": block_key})
        
        if not block_data:
            return False

        if datetime.utcnow() > block_data["expires_at"]:
            await self.db.blocked.delete_one({"pair": block_key})
            return False

        return True

    async def block_users(self, user1_id: str, user2_id: str, duration: timedelta):
        block_key = ",".join(sorted([user1_id, user2_id]))
        await self.db.blocked.update_one(
            {"pair": block_key},
            {
                "$set": {
                    "expires_at": datetime.utcnow() + duration,
                    "created_at": datetime.utcnow()
                }
            },
            upsert=True
        )