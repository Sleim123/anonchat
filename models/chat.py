from datetime import datetime
from typing import Dict
from pydantic import BaseModel

class Chat(BaseModel):
    id: str
    user1_id: str
    user2_id: str
    created_at: datetime = datetime.utcnow()
    message_map: Dict[int, int] = {}
    
    class Config:
        arbitrary_types_allowed = True

    def to_dict(self):
        return {
            "id": self.id,
            "user1_id": self.user1_id,
            "user2_id": self.user2_id,
            "created_at": self.created_at,
            "message_map": self.message_map
        }

    @staticmethod
    def from_dict(data: dict):
        if not data:
            return None
        return Chat(**data)