from datetime import datetime
from typing import Optional, Any, Dict
from pydantic import BaseModel

class Message(BaseModel):
    """
    Модель сообщения для анонимного чата
    """
    id: str
    chat_id: str
    sender_id: str
    content: Any  # Может содержать текст или информацию о медиафайле
    message_type: str  # text, photo, video, document, audio, voice, sticker, video_note
    original_message_id: int  # ID оригинального сообщения в Telegram
    forwarded_message_id: int  # ID пересланного сообщения
    created_at: datetime = datetime.utcnow()
    
    # Дополнительные поля для разных типов сообщений
    file_id: Optional[str] = None  # Для медиафайлов
    file_size: Optional[int] = None
    mime_type: Optional[str] = None
    caption: Optional[str] = None
    metadata: Dict[str, Any] = {}  # Для хранения дополнительных данных

    class Config:
        arbitrary_types_allowed = True

    @staticmethod
    def from_telegram_message(telegram_message, chat_id: str, forwarded_message_id: int) -> 'Message':
        """
        Создает объект Message из telegram.Message
        """
        message_type = Message._determine_message_type(telegram_message)
        content = Message._extract_content(telegram_message, message_type)
        
        return Message(
            id=str(telegram_message.message_id),
            chat_id=chat_id,
            sender_id=str(telegram_message.from_user.id),
            content=content,
            message_type=message_type,
            original_message_id=telegram_message.message_id,
            forwarded_message_id=forwarded_message_id,
            file_id=Message._get_file_id(telegram_message, message_type),
            file_size=Message._get_file_size(telegram_message, message_type),
            mime_type=Message._get_mime_type(telegram_message, message_type),
            caption=telegram_message.caption if hasattr(telegram_message, 'caption') else None,
            metadata=Message._extract_metadata(telegram_message, message_type)
        )

    @staticmethod
    def _determine_message_type(telegram_message) -> str:
        """
        Определяет тип сообщения
        """
        types = ['text', 'photo', 'video', 'document', 
                'audio', 'voice', 'sticker', 'video_note']
        
        for msg_type in types:
            if hasattr(telegram_message, msg_type) and getattr(telegram_message, msg_type):
                return msg_type
        return 'unknown'

    @staticmethod
    def _extract_content(telegram_message, message_type: str) -> Any:
        """
        Извлекает содержимое сообщения в зависимости от его типа
        """
        if message_type == 'text':
            return telegram_message.text
        elif message_type == 'photo':
            return [photo.file_id for photo in telegram_message.photo]
        elif message_type in ['video', 'document', 'audio', 'voice', 'sticker', 'video_note']:
            return getattr(telegram_message, message_type).file_id
        return None

    @staticmethod
    def _get_file_id(telegram_message, message_type: str) -> Optional[str]:
        """
        Получает file_id для медиафайлов
        """
        if message_type == 'photo':
            return telegram_message.photo[-1].file_id if telegram_message.photo else None
        elif message_type in ['video', 'document', 'audio', 'voice', 'sticker', 'video_note']:
            media = getattr(telegram_message, message_type)
            return media.file_id if media else None
        return None

    @staticmethod
    def _get_file_size(telegram_message, message_type: str) -> Optional[int]:
        """
        Получает размер файла для медиафайлов
        """
        if message_type == 'photo':
            return telegram_message.photo[-1].file_size if telegram_message.photo else None
        elif message_type in ['video', 'document', 'audio', 'voice', 'sticker', 'video_note']:
            media = getattr(telegram_message, message_type)
            return media.file_size if media else None
        return None

    @staticmethod
    def _get_mime_type(telegram_message, message_type: str) -> Optional[str]:
        """
        Получает MIME-тип для медиафайлов
        """
        if message_type == 'document':
            return telegram_message.document.mime_type
        elif message_type == 'audio':
            return telegram_message.audio.mime_type
        elif message_type == 'video':
            return telegram_message.video.mime_type
        return None

    @staticmethod
    def _extract_metadata(telegram_message, message_type: str) -> Dict[str, Any]:
        """
        Извлекает дополнительные метаданные в зависимости от типа сообщения
        """
        metadata = {}

        if message_type == 'video':
            metadata.update({
                'duration': telegram_message.video.duration,
                'width': telegram_message.video.width,
                'height': telegram_message.video.height
            })
        elif message_type == 'audio':
            metadata.update({
                'duration': telegram_message.audio.duration,
                'performer': telegram_message.audio.performer,
                'title': telegram_message.audio.title
            })
        elif message_type == 'voice':
            metadata.update({
                'duration': telegram_message.voice.duration
            })
        elif message_type == 'sticker':
            metadata.update({
                'emoji': telegram_message.sticker.emoji,
                'set_name': telegram_message.sticker.set_name,
                'is_animated': telegram_message.sticker.is_animated,
                'is_video': telegram_message.sticker.is_video
            })

        # Добавляем общие метаданные
        if hasattr(telegram_message, 'forward_from'):
            metadata['forwarded'] = True
            metadata['forward_date'] = telegram_message.forward_date

        if hasattr(telegram_message, 'reply_to_message'):
            metadata['is_reply'] = True
            metadata['reply_to_message_id'] = telegram_message.reply_to_message.message_id

        return metadata

    def to_dict(self) -> Dict[str, Any]:
        """
        Преобразует объект Message в словарь для сохранения в базе данных
        """
        return {
            "id": self.id,
            "chat_id": self.chat_id,
            "sender_id": self.sender_id,
            "content": self.content,
            "message_type": self.message_type,
            "original_message_id": self.original_message_id,
            "forwarded_message_id": self.forwarded_message_id,
            "created_at": self.created_at,
            "file_id": self.file_id,
            "file_size": self.file_size,
            "mime_type": self.mime_type,
            "caption": self.caption,
            "metadata": self.metadata
        }

    @staticmethod
    def from_dict(data: Dict[str, Any]) -> 'Message':
        """
        Создает объект Message из словаря
        """
        return Message(**data)