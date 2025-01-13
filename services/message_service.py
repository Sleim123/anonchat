from typing import Optional
from telegram import Message, Update
from core.queue_manager import MessageQueue
import re
import logging

class MessageService:
    def __init__(self, queue_manager: MessageQueue):
        self.queue = queue_manager

    async def handle_message(self, message: Message, other_user_id: str) -> bool:
        try:
            # Проверка на запрещенный контент
            if not self.validate_message(message):
                return False

            # Добавляем сообщение в очередь
            await self.queue.add_message(other_user_id, message)
            return True
        except Exception as e:
            logging.error(f"Error handling message: {e}")
            return False

    def validate_message(self, message: Message) -> bool:
        if message.text:
            # Проверка на @username
            if "@" in message.text and not message.text.startswith("/link"):
                return False
            
            # Проверка на ссылки
            if re.search(r"(https?://|www\.[a-zA-Z]|[a-zA-Z]\.[a-z]{2,})", 
                        message.text.replace(" ", "")):
                return False

        # Проверка на поддерживаемые типы сообщений
        supported_types = ['text', 'photo', 'video', 'document', 
                         'audio', 'voice', 'sticker', 'video_note']
        
        message_type = next((t for t in supported_types 
                           if getattr(message, t, None)), None)
        return message_type is not None

    async def format_message(self, message: Message) -> dict:
        """Подготовка сообщения для отправки"""
        base_params = {
            "protect_content": True,
            "caption_entities": message.caption_entities if hasattr(message, 'caption') else None,
        }

        if message.reply_to_message:
            base_params["reply_to_message_id"] = message.message_id

        return {
            "text": message.text if message.text else None,
            "caption": message.caption if hasattr(message, 'caption') else None,
            **base_params
        }