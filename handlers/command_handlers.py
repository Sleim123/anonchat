from telegram import Update
from telegram.ext import ContextTypes
from services.user_service import UserService
from services.chat_service import ChatService
from services.matching_service import MatchingService
from utils.keyboards import Keyboards
from utils.helpers import TimeHelper
from config.settings import Config
import logging

class CommandHandler:
    def __init__(self, user_service: UserService, chat_service: ChatService, matching_service: MatchingService):
        self.user_service = user_service
        self.chat_service = chat_service
        self.matching_service = matching_service
        self.keyboards = Keyboards()

    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = str(update.effective_user.id)
        user = await self.user_service.get_user(user_id)
        
        if not user:
            user = await self.user_service.create_user(user_id)

        welcome_text = (
            "*👋 Добро пожаловать в Анонимный чат!*\n\n"
            "*🛡 Шифрование данных*\n"
            "*🎭 Полная анонимность*\n"
            "*📙 Интересы для общения*\n"
            "*💅 Поиск собеседника по полу*\n\n"
            "_Просим соблюдать правила этикета в общении._"
        )

        await update.message.reply_text(
            welcome_text,
            parse_mode='Markdown',
            reply_markup=self.keyboards.get_main_keyboard()
        )

    async def search(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = str(update.effective_user.id)
        user = await self.user_service.get_user(user_id)

        if user.status == "banned":
            await update.message.reply_text(
                "*⚠️ Невозможно начать поиск.*\n\n*Вы были заблокированы администратором.*",
                parse_mode='Markdown'
            )
            return

        if user.status == "chatting":
            await update.message.reply_text(
                "🥷 *У вас уже есть собеседник*\n\n/next — _искать нового собеседника_\n/stop — _завершить диалог_",
                parse_mode='Markdown',
                reply_markup=self.keyboards.get_main_keyboard(True)
            )
            return

        if user.status == "searching":
            await update.message.reply_text(
                "_Мы уже ищем собеседника..._",
                parse_mode='Markdown',
                reply_markup=self.keyboards.get_main_keyboard(True)
            )
            return

        logging.info(f"(!) Пользователь {user_id} начал поиск собеседника. (!)")
        await self.user_service.update_user_status(user_id, "searching")

        match = await self.matching_service.find_match(user)
        if match:
            await self.chat_service.create_chat(user_id, match.id)
            await self.user_service.update_user_status(user_id, "chatting")
            await self.user_service.update_user_status(match.id, "chatting")

            await update.message.reply_text(
                "*🔎 Собеседник найден!*\n\n/next — _искать нового собеседника_\n/stop — _завершить диалог_",
                parse_mode='Markdown',
                reply_markup=self.keyboards.get_main_keyboard(True)
            )

            await context.bot.send_message(
                chat_id=match.id,
                text="*🔎 Собеседник найден!*\n\n/next — _искать нового собеседника_\n/stop — _завершить диалог_",
                parse_mode='Markdown',
                reply_markup=self.keyboards.get_main_keyboard(True)
            )
        else:
            await update.message.reply_text(
                "_Свободных собеседников нет. Поиск займет больше времени, чем обычно..._",
                parse_mode='Markdown',
                reply_markup=self.keyboards.get_main_keyboard(True)
            )

    async def stop(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = str(update.effective_user.id)
        chat = await self.chat_service.get_chat(user_id)

        if not chat:
            await update.message.reply_text(
                "🚫 *Данную команду можно использовать только в чате!*\n\n/search — _искать нового собеседника_",
                parse_mode='Markdown',
                reply_markup=self.keyboards.get_main_keyboard()
            )
            return

        other_user_id = chat.user2_id if chat.user1_id == user_id else chat.user1_id
        await self.chat_service.end_chat(chat.id)

        await self.user_service.update_user_status(user_id, "normal")
        await self.user_service.update_user_status(other_user_id, "normal")

        await update.message.reply_text(
            "🛑 *Вы завершили чат*\n\n/search — _искать нового собеседника_",
            parse_mode='Markdown',
            reply_markup=self.keyboards.get_main_keyboard()
        )

        await context.bot.send_message(
            chat_id=other_user_id,
            text="🛑 *Ваш собеседник завершил чат*\n\n/search — _искать нового собеседника_",
            parse_mode='Markdown',
            reply_markup=self.keyboards.get_main_keyboard()
        )

    async def next(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = str(update.effective_user.id)
        chat = await self.chat_service.get_chat(user_id)

        if not chat:
            await update.message.reply_text(
                "🚫 *Данную команду можно использовать только в чате!*\n\n/search — _искать нового собеседника_",
                parse_mode='Markdown',
                reply_markup=self.keyboards.get_main_keyboard()
            )
            return

        other_user_id = chat.user2_id if chat.user1_id == user_id else chat.user1_id
        await self.chat_service.end_chat(chat.id)

        await self.user_service.update_user_status(user_id, "searching")
        await self.user_service.update_user_status(other_user_id, "normal")

        await update.message.reply_text(
            "*🔎 Ищем нового собеседника...*",
            parse_mode='Markdown',
            reply_markup=self.keyboards.get_main_keyboard(True)
        )

        await context.bot.send_message(
            chat_id=other_user_id,
            text="🛑 *Ваш собеседник завершил чат*\n\n/search — _искать нового собеседника_",
            parse_mode='Markdown',
            reply_markup=self.keyboards.get_main_keyboard()
        )

        await self.search(update, context)

    async def profile(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = str(update.effective_user.id)
        user = await self.user_service.get_user(user_id)

        if not user:
            await update.message.reply_text(
                "Профиль не найден. Попробуйте снова.",
                parse_mode='Markdown'
            )
            return

        profile_text = (
            f"*👤 Профиль*\n\n"
            f"Имя: {user.name}\n"
            f"Пол: {user.gender}\n"
            f"Возраст: {user.age}\n"
            f"Интересы: {', '.join(user.interests)}"
        )

        await update.message.reply_text(
            profile_text,
            parse_mode='Markdown',
            reply_markup=self.keyboards.get_profile_keyboard()
        )

    async def admin_commands(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.effective_user.id
        if user_id != Config.ADMIN_ID:
            return

        args = context.args
        if len(args) != 1:
            await update.message.reply_text(
                "_Некорректный формат команды. Используйте команду в формате: /admin <команда>_",
                parse_mode='Markdown'
            )
            return

        command = args[0]
        if command == 'ban':
            await self.ban(update, context)
        elif command == 'unban':
            await self.unban(update, context)
        elif command == 'premium':
            await self.premium(update, context)
        elif command == 'unpremium':
            await self.unpremium(update, context)
        elif command == 'stats':
            await self.stats(update, context)
        elif command == 'debug':
            await self.debug(update, context)
        elif command == 'timeout':
            await self.timeout(update, context)
        elif command == 'getid':
            await self.getid(update, context)
        else:
            await update.message.reply_text(
                "_Неизвестная команда. Попробуйте снова._",
                parse_mode='Markdown'
            )