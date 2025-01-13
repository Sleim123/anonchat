from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel

class User(BaseModel):
    id: str
    status: str = "normal"
    chat_with: Optional[str] = None
    interests: List[str] = []
    gender: Optional[str] = None
    premium: bool = False
    chats_count: int = 0
    likes: int = 0
    dislikes: int = 0
    last_activity: datetime = datetime.utcnow()
    
    class Config:
        arbitrary_types_allowed = True

    def to_dict(self):
        return {
            "id": self.id,
            "status": self.status,
            "chat_with": self.chat_with,
            "interests": self.interests,
            "gender": self.gender,
            "premium": self.premium,
            "chats_count": self.chats_count,
            "likes": self.likes,
            "dislikes": self.dislikes,
            "last_activity": self.last_activity
        }

    @staticmethod
    def from_dict(data: dict):
        if not data:
            return None
        return User(**data)