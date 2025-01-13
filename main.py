import asyncio
import logging
import signal
from typing import Dict, Any
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler as TelegramCommandHandler,
    MessageHandler as TelegramMessageHandler,
    CallbackQueryHandler,
    filters
)
from config.settings import Config
from core.database import DatabaseManager
from core.redis_cache import RedisCache
from core.queue_manager import MessageQueue
from handlers.command_handlers import CommandHandler
from handlers.message_handlers import MessageHandler as CustomMessageHandler
from services.user_service import UserService
from services.chat_service import ChatService
from services.message_service import MessageService
from services.matching_service import MatchingService

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

class AnonymousChatBot:
    def __init__(self):
        self.db = DatabaseManager()
        self.cache = RedisCache()
        self.message_queue = MessageQueue()
        
        self.user_service = UserService(self.db, self.cache)
        self.chat_service = ChatService(self.db, self.cache)
        self.message_service = MessageService(self.message_queue)
        self.matching_service = MatchingService(self.db)
        
        self.command_handler = CommandHandler(
            self.user_service,
            self.chat_service,
            self.matching_service
        )
        self.message_handler = CustomMessageHandler(
            self.user_service,
            self.chat_service,
            self.message_service
        )
        
        self.application = None
        self.is_running = False
        self._queue_task = None
        self._shutdown_event = asyncio.Event()

    async def setup_handlers(self):
        if not self.application:
            return

        self.application.add_handler(TelegramCommandHandler("start", self.command_handler.start), group=1)
        self.application.add_handler(TelegramCommandHandler("search", self.command_handler.search), group=1)
        self.application.add_handler(TelegramCommandHandler("stop", self.command_handler.stop), group=1)
        self.application.add_handler(TelegramCommandHandler("next", self.command_handler.next), group=1)
        self.application.add_handler(TelegramCommandHandler("profile", self.command_handler.profile), group=1)

        self.application.add_handler(
            TelegramMessageHandler(
                filters.TEXT & ~filters.COMMAND,
                self.message_handler.handle_message
            ),
            group=2
        )

        media_filters = (
            filters.PHOTO |
            filters.VIDEO |
            filters.VOICE |
            filters.AUDIO |
            filters.Document.ALL |
            filters.Sticker.ALL
        )
        self.application.add_handler(
            TelegramMessageHandler(
                media_filters,
                self.message_handler.handle_message
            ),
            group=3
        )

        self.application.add_handler(
            CallbackQueryHandler(self.message_handler.handle_callback),
            group=4
        )

    async def initialize(self):
        """Инициализация компонентов бота"""
        try:
            await self.db.connect()
            logger.info("Database connection established")
            
            await self.cache.connect()
            logger.info("Redis connection established")
            
            self._queue_task = asyncio.create_task(self.message_queue.start_processing())
            logger.info("Message queue processor started")
        except Exception as e:
            logger.error(f"Error during initialization: {e}")
            await self.shutdown()
            raise

    async def shutdown(self):
        """Корректное завершение работы бота"""
        if not self.is_running:
            return

        self.is_running = False
        self._shutdown_event.set()

        # Останавливаем очередь сообщений
        if self._queue_task and not self._queue_task.done():
            self.message_queue.processing = False
            try:
                self._queue_task.cancel()
                await asyncio.shield(self._queue_task)
            except asyncio.CancelledError:
                pass

        # Останавливаем компоненты в правильном порядке
        components = [
            (self.application, "Application"),
            (self.message_queue, "Message queue"),
            (self.cache, "Redis"),
            (self.db, "Database")
        ]

        for component, name in components:
            if component:
                try:
                    if hasattr(component, 'stop'):
                        await component.stop()
                    elif hasattr(component, 'close'):
                        await component.close()
                    logger.info(f"{name} stopped successfully")
                except Exception as e:
                    logger.error(f"Error stopping {name}: {e}")

    async def run(self):
        """Запуск бота"""
        try:
            # Создаем приложение
            self.application = Application.builder().token(Config.BOT_TOKEN).build()
            
            # Инициализируем компоненты
            await self.initialize()
            
            # Настраиваем обработчики
            await self.setup_handlers()

            # Устанавливаем флаг работы
            self.is_running = True
            logger.info("Starting bot...")

            # Запускаем приложение
            await self.application.initialize()
            await self.application.start()
            
            # Запускаем polling в бесконечном цикле
            while not self._shutdown_event.is_set():
                try:
                    await self.application.updater.start_polling()
                    await self._shutdown_event.wait()
                except Exception as e:
                    logger.error(f"Polling error: {e}")
                    if not self._shutdown_event.is_set():
                        await asyncio.sleep(1)
                    else:
                        break

        except Exception as e:
            logger.error(f"Error running bot: {e}")
            raise
        finally:
            await self.shutdown()

def main():
    """Главная функция запуска бота"""
    bot = AnonymousChatBot()
    
    def signal_handler(signum, frame):
        """Обработчик сигналов"""
        if bot.is_running:
            logger.info(f"Received signal {signum}")
            # Используем правильный способ установки события в event loop
            loop = asyncio.get_running_loop()
            loop.call_soon_threadsafe(bot._shutdown_event.set)

    # Регистрируем обработчики сигналов
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    try:
        # Запускаем бота в отдельном event loop
        asyncio.run(bot.run())
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
    except Exception as e:
        logger.error(f"Bot stopped due to error: {e}")

if __name__ == "__main__":
    main()