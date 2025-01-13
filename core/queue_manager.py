import asyncio
from typing import Dict, List, Set
from telegram import Message
from config.settings import Config
import logging

class MessageQueue:
    def __init__(self):
        self.queues: Dict[str, List[Message]] = {}
        self.processing = False
        self._tasks: Set[asyncio.Task] = set()
        self.batch_size = Config.BATCH_SIZE
        self.process_interval = Config.PROCESS_INTERVAL

    async def add_message(self, chat_id: str, message: Message):
        if chat_id not in self.queues:
            self.queues[chat_id] = []
        
        self.queues[chat_id].append(message)
        
        if len(self.queues[chat_id]) >= self.batch_size:
            await self.process_queue(chat_id)

    async def process_queue(self, chat_id: str):
        if not self.queues.get(chat_id):
            return

        try:
            messages = self.queues[chat_id][:self.batch_size]
            self.queues[chat_id] = self.queues[chat_id][self.batch_size:]
            
            tasks = [self.send_message(msg) for msg in messages]
            await asyncio.gather(*tasks, return_exceptions=True)
        except Exception as e:
            logging.error(f"Error processing message queue: {e}")

    async def send_message(self, message: Message):
        try:
            await message.copy(
                chat_id=message.chat_id,
                reply_to_message_id=message.message_id if Config.REPLY_TO_MESSAGES else None
            )
        except Exception as e:
            logging.error(f"Error sending message: {e}")

    async def start_processing(self):
        """Запуск обработки сообщений в очереди"""
        self.processing = True
        while self.processing:
            try:
                await asyncio.sleep(self.process_interval)
                for chat_id in list(self.queues.keys()):
                    await self.process_queue(chat_id)
            except asyncio.CancelledError:
                logging.info("Message queue processing cancelled")
                break
            except Exception as e:
                logging.error(f"Error in message queue processing: {e}")
                continue

    async def stop(self):
        """Остановка обработки очереди и очистка ресурсов"""
        try:
            self.processing = False
            # Обработка оставшихся сообщений
            for chat_id in list(self.queues.keys()):
                if self.queues[chat_id]:
                    await self.process_queue(chat_id)
            self.queues.clear()
            logging.info("Message queue stopped successfully")
        except Exception as e:
            logging.error(f"Error stopping message queue: {e}")
            raise

    async def get_queue_size(self, chat_id: str) -> int:
        """Получить размер очереди для конкретного чата"""
        return len(self.queues.get(chat_id, []))

    async def clear_queue(self, chat_id: str):
        """Очистить очередь сообщений для конкретного чата"""
        try:
            if chat_id in self.queues:
                self.queues[chat_id].clear()
                logging.info(f"Queue cleared for chat {chat_id}")
        except Exception as e:
            logging.error(f"Error clearing queue for chat {chat_id}: {e}")

    async def process_batch(self, messages: List[Message]):
        """Обработка пакета сообщений"""
        try:
            results = await asyncio.gather(
                *[self.send_message(msg) for msg in messages],
                return_exceptions=True
            )
            # Обработка результатов
            for msg, result in zip(messages, results):
                if isinstance(result, Exception):
                    logging.error(f"Failed to process message {msg.message_id}: {result}")
        except Exception as e:
            logging.error(f"Error processing message batch: {e}")

    async def send_message(self, message: Message):
        """Отправка отдельного сообщения"""
        try:
            if not message or not message.chat_id:
                logging.error("Invalid message object")
                return

            # Получаем объект бота из контекста сообщения
            bot = message.get_bot()
            
            # Определяем тип сообщения и отправляем соответствующим способом
            if message.text:
                # Текстовое сообщение
                await bot.send_message(
                    chat_id=message.chat_id,
                    text=message.text,
                    parse_mode=message.parse_mode,
                    reply_markup=message.reply_markup,
                    disable_web_page_preview=True
                )
            elif message.photo:
                # Фотография
                await bot.send_photo(
                    chat_id=message.chat_id,
                    photo=message.photo[-1].file_id,
                    caption=message.caption,
                    parse_mode=message.parse_mode,
                    reply_markup=message.reply_markup
                )
            elif message.video:
                # Видео
                await bot.send_video(
                    chat_id=message.chat_id,
                    video=message.video.file_id,
                    caption=message.caption,
                    parse_mode=message.parse_mode,
                    reply_markup=message.reply_markup
                )
            elif message.voice:
                # Голосовое сообщение
                await bot.send_voice(
                    chat_id=message.chat_id,
                    voice=message.voice.file_id,
                    caption=message.caption,
                    parse_mode=message.parse_mode,
                    reply_markup=message.reply_markup
                )
            elif message.audio:
                # Аудио файл
                await bot.send_audio(
                    chat_id=message.chat_id,
                    audio=message.audio.file_id,
                    caption=message.caption,
                    parse_mode=message.parse_mode,
                    reply_markup=message.reply_markup
                )
            elif message.document:
                # Документ
                await bot.send_document(
                    chat_id=message.chat_id,
                    document=message.document.file_id,
                    caption=message.caption,
                    parse_mode=message.parse_mode,
                    reply_markup=message.reply_markup
                )
            elif message.sticker:
                # Стикер
                await bot.send_sticker(
                    chat_id=message.chat_id,
                    sticker=message.sticker.file_id,
                    reply_markup=message.reply_markup
                )
            elif message.animation:
                # GIF анимация
                await bot.send_animation(
                    chat_id=message.chat_id,
                    animation=message.animation.file_id,
                    caption=message.caption,
                    parse_mode=message.parse_mode,
                    reply_markup=message.reply_markup
                )
            elif message.video_note:
                # Видео-заметка (круглое видео)
                await bot.send_video_note(
                    chat_id=message.chat_id,
                    video_note=message.video_note.file_id,
                    reply_markup=message.reply_markup
                )
            
            logging.info(f"Message {message.message_id} sent successfully to chat {message.chat_id}")
            
            # Добавляем небольшую задержку между сообщениями для избежания flood control
            await asyncio.sleep(0.1)
            
        except Exception as e:
            error_msg = f"Error sending message {message.message_id} to chat {message.chat_id}: {str(e)}"
            logging.error(error_msg)
            
            # Обработка специфических ошибок Telegram
            if "bot was blocked by the user" in str(e).lower():
                # Пользователь заблокировал бота
                logging.warning(f"Bot was blocked by user in chat {message.chat_id}")
                # Здесь можно добавить логику обработки блокировки
                return
                
            if "chat not found" in str(e).lower():
                # Чат не найден
                logging.warning(f"Chat {message.chat_id} not found")
                # Здесь можно добавить логику обработки отсутствующего чата
                return
                
            if "flood control exceeded" in str(e).lower():
                # Превышен лимит сообщений
                logging.warning("Flood control exceeded, adding delay")
                await asyncio.sleep(5)  # Увеличиваем задержку
                # Можно повторить отправку
                await self.add_message(message.chat_id, message)
                return
                
            # Другие ошибки
            raise

    def is_processing(self) -> bool:
        """Проверка статуса обработки очереди"""
        return self.processing

    def get_total_messages(self) -> int:
        """Получить общее количество сообщений во всех очередях"""
        return sum(len(queue) for queue in self.queues.values())

    async def handle_error(self, error: Exception, context: Dict = None):
        """Обработка ошибок очереди"""
        logging.error(f"Queue error: {error}")
        if context:
            logging.error(f"Error context: {context}")
        # Здесь можно добавить дополнительную логику обработки ошибок
        # Например, отправку уведомлений администратору или запись в специальный лог

    async def __aenter__(self):
        """Асинхронный контекстный менеджер - вход"""
        if not self.processing:
            asyncio.create_task(self.start_processing())
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Асинхронный контекстный менеджер - выход"""
        await self.stop()
        if exc_val:
            await self.handle_error(exc_val)