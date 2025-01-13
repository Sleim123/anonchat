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
        # Инициализация компонентов
        self.db = DatabaseManager()
        self.cache = RedisCache()
        self.message_queue = MessageQueue()
        
        # Инициализация сервисов
        self.user_service = UserService(self.db, self.cache)
        self.chat_service = ChatService(self.db, self.cache)
        self.message_service = MessageService(self.message_queue)
        self.matching_service = MatchingService(self.db)
        
        # Инициализация обработчиков
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
        self._stop_event = asyncio.Event()

    async def setup_handlers(self):
        """Настройка обработчиков команд и сообщений"""
        # Обработчики команд (высший приоритет)
        self.application.add_handler(TelegramCommandHandler("start", self.command_handler.start), group=1)
        self.application.add_handler(TelegramCommandHandler("search", self.command_handler.search), group=1)
        self.application.add_handler(TelegramCommandHandler("stop", self.command_handler.stop), group=1)
        self.application.add_handler(TelegramCommandHandler("next", self.command_handler.next), group=1)
        self.application.add_handler(TelegramCommandHandler("profile", self.command_handler.profile), group=1)

        # Обработчики сообщений (средний приоритет)
        self.application.add_handler(
            TelegramMessageHandler(
                filters.TEXT & ~filters.COMMAND,
                self.message_handler.handle_message
            ),
            group=2
        )

        # Обработчики медиа (низкий приоритет)
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

        # Обработчик callback-запросов от inline-клавиатуры
        self.application.add_handler(
            CallbackQueryHandler(self.message_handler.handle_callback),
            group=4
        )

    async def initialize(self):
        """Инициализация компонентов бота"""
        await self.db.connect()
        logger.info("Database connection established")
        
        await self.cache.connect()
        logger.info("Redis connection established")
        
        await self.message_queue.__aenter__()
        logger.info("Message queue processor started")

    async def shutdown(self):
        """Корректное завершение работы бота"""
        if not self.is_running:
            return

        self.is_running = False
        self._stop_event.set()

        if self.application:
            try:
                await self.application.stop()
                await self.application.shutdown()
                logger.info("Application stopped successfully")
            except Exception as e:
                logger.error(f"Error stopping application: {e}")

        try:
            await self.message_queue.__aexit__(None, None, None)
            logger.info("Message queue stopped successfully")
        except Exception as e:
            logger.error(f"Error stopping message queue: {e}")

        try:
            await self.cache.close()
            logger.info("Redis connection closed successfully")
        except Exception as e:
            logger.error(f"Error closing Redis: {e}")

        try:
            await self.db.close()
            logger.info("Database connection closed successfully")
        except Exception as e:
            logger.error(f"Error closing database: {e}")

    async def start(self):
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
            
            # Запускаем polling в отдельной задаче
            polling_task = asyncio.create_task(
                self.application.run_polling(
                    allowed_updates=Update.ALL_TYPES,
                    drop_pending_updates=True,
                    stop_signals=()  # Отключаем встроенную обработку сигналов
                )
            )

            # Ждем сигнала остановки
            await self._stop_event.wait()
            
            # Отменяем задачу polling
            polling_task.cancel()
            try:
                await polling_task
            except asyncio.CancelledError:
                pass

        except Exception as e:
            logger.error(f"Error starting bot: {e}")
            raise
        finally:
            await self.shutdown()

def main():
    bot = AnonymousChatBot()
    
    def signal_handler(signum, frame):
        """Обработчик сигналов"""
        if bot.is_running:
            logger.info(f"Received signal {signum}")
            # Устанавливаем событие остановки
            asyncio.get_event_loop().call_soon_threadsafe(bot._stop_event.set)

    # Регистрируем обработчики сигналов
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    try:
        # Запускаем бота
        asyncio.run(bot.start())
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
    except Exception as e:
        logger.error(f"Bot stopped due to error: {e}")

if __name__ == "__main__":
    main()