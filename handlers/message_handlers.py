from telegram import Update
from telegram.ext import ContextTypes
from services.user_service import UserService
from services.chat_service import ChatService
from services.message_service import MessageService
from utils.keyboards import Keyboards
import re
import logging

class MessageHandler:
    def __init__(
        self,
        user_service: UserService,
        chat_service: ChatService,
        message_service: MessageService
    ):
        self.user_service = user_service
        self.chat_service = chat_service
        self.message_service = message_service
        self.keyboards = Keyboards()

    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Основной обработчик всех входящих сообщений"""
        if not update.message:
            return

        user_id = str(update.effective_user.id)
        user = await self.user_service.get_user(user_id)

        if not user:
            return

        # Обработка текстовых команд с клавиатуры
        if update.message.text:
            await self._handle_keyboard_commands(update, context, user)
            return

        # Обработка сообщений в активном чате
        if user.status == "chatting" and user.chat_with:
            await self._handle_chat_message(update, context, user)

    async def _handle_keyboard_commands(self, update: Update, context: ContextTypes.DEFAULT_TYPE, user):
        """Обработка команд с клавиатуры"""
        text = update.message.text

        commands = {
            "🔎 Поиск собеседника": self._handle_search,
            "❌ Остановить поиск": self._handle_stop_search,
            "🎭 Поиск по полу": self._handle_gender_search,
            "📙 Интересы": self._handle_
            ,
            "💼 Профиль": self._handle_profile,
            "👨‍🦰 Поиск М": lambda u, c, user: self._handle_gender_specific_search(u, c, user, "m"),
            "👩‍🦱 Поиск Д": lambda u, c, user: self._handle_gender_specific_search(u, c, user, "w"),
            "◀️ Вернуться назад": self._handle_back
        }

        handler = commands.get(text)
        if handler:
            await handler(update, context, user)

    async def _handle_chat_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE, user):
        """Обработка сообщений в активном чате"""
        try:
            # Проверка на запрещенный контент
            if not await self.message_service.validate_message(update.message):
                await update.message.reply_text(
                    "⚠️ *Это сообщение нарушает правила чата.*",
                    parse_mode='Markdown'
                )
                return

            other_user = await self.user_service.get_user(user.chat_with)
            if not other_user or other_user.status != "chatting":
                await update.message.reply_text(
                    "🚫 *Чат был завершен.*",
                    parse_mode='Markdown',
                    reply_markup=self.keyboards.get_main_keyboard()
                )
                user.status = "normal"
                user.chat_with = None
                await self.user_service.update_user(user)
                return

            # Отправка сообщения собеседнику
            await self.message_service.handle_message(update.message, user.chat_with)

        except Exception as e:
            logging.error(f"Error in chat message handling: {e}")
            await update.message.reply_text(
                "⚠️ *Произошла ошибка при отправке сообщения.*",
                parse_mode='Markdown'
            )

    async def _handle_search(self, update: Update, context: ContextTypes.DEFAULT_TYPE, user):
        """Обработка команды поиска собеседника"""
        if user.status == "chatting":
            await update.message.reply_text(
                "🥷 *У вас уже есть собеседник*\n\n/next — _искать нового собеседника_\n/stop — _завершить диалог_",
                parse_mode='Markdown'
            )
            return

        if user.status == "searching":
            await update.message.reply_text(
                "_Мы уже ищем собеседника..._",
                parse_mode='Markdown',
                reply_markup=self.keyboards.get_main_keyboard(True)
            )
            return

        user.status = "searching"
        await self.user_service.update_user(user)

        await update.message.reply_text(
            "_Ищем собеседника..._",
            parse_mode='Markdown',
            reply_markup=self.keyboards.get_main_keyboard(True)
        )

    async def _handle_stop_search(self, update: Update, context: ContextTypes.DEFAULT_TYPE, user):
        """Обработка команды остановки поиска"""
        if user.status != "searching":
            await update.message.reply_text(
                "_Вы не в поиске собеседника_",
                parse_mode='Markdown',
                reply_markup=self.keyboards.get_main_keyboard()
            )
            return

        user.status = "normal"
        await self.user_service.update_user(user)

        await update.message.reply_text(
            "_Поиск остановлен_",
            parse_mode='Markdown',
            reply_markup=self.keyboards.get_main_keyboard()
        )

    async def _handle_gender_search(self, update: Update, context: ContextTypes.DEFAULT_TYPE, user):
        """Обработка команды поиска по полу"""
        if not user.premium:
            await update.message.reply_text(
                "*🔒 Функция доступна только для Premium пользователей*",
                parse_mode='Markdown',
                reply_markup=self.keyboards.get_main_keyboard()
            )
            return

        await update.message.reply_text(
            "_Выберите пол для поиска:_",
            parse_mode='Markdown',
            reply_markup=self.keyboards.get_gender_search_keyboard()
        )

    async def _handle_gender_specific_search(self, update: Update, context: ContextTypes.DEFAULT_TYPE, user, gender):
        """Обработка поиска по конкретному полу"""
        if not user.premium:
            return

        user.status = "searching"
        user.search_gender = gender
        await self.user_service.update_user(user)

        gender_text = "мужского" if gender == "m" else "женского"
        await update.message.reply_text(
            f"_Ищем собеседника {gender_text} пола..._",
            parse_mode='Markdown',
            reply_markup=self.keyboards.get_main_keyboard(True)
        )

    async def _handle_interests(self, update: Update, context: ContextTypes.DEFAULT_TYPE, user):
        """Обработка команды интересов"""
        await update.message.reply_text(
            "*📙 Интересы поиска*\n\n_Выберите ваши интересы:_",
            parse_mode='Markdown',
            reply_markup=self.keyboards.get_interests_keyboard(user.interests)
        )

    async def _handle_profile(self, update: Update, context: ContextTypes.DEFAULT_TYPE, user):
        """Обработка команды профиля"""
        await context.bot.commands.profile(update, context)

    async def _handle_back(self, update: Update, context: ContextTypes.DEFAULT_TYPE, user):
        """Обработка команды возврата в главное меню"""
        await update.message.reply_text(
            "_Вы вернулись в главное меню_",
            parse_mode='Markdown',
            reply_markup=self.keyboards.get_main_keyboard()
        )

    # В класс MessageHandler добавляем новый метод:
    async def handle_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработка callback запросов от inline кнопок"""
        if not update.callback_query:
            return

        query = update.callback_query
        user_id = str(update.effective_user.id)
        user = await self.user_service.get_user(user_id)

        if not user:
            await query.answer("Ошибка: пользователь не найден")
            return

        try:
            data = query.data

            if data.startswith('interest_'):
                await self._handle_interest_selection(query, user)
            elif data == 'reset_interests':
                await self._handle_interest_reset(query, user)
            elif data == 'profile_settings':
                await self._handle_profile_settings(query, user)
            elif data.startswith('like_'):
                await self._handle_like(query, user)
            elif data.startswith('dislike_'):
                await self._handle_dislike(query, user)
            else:
                await query.answer("Неизвестное действие")

        except Exception as e:
            logging.error(f"Error handling callback query: {e}")
            await query.answer("Произошла ошибка при обработке запроса")

    async def _handle_interest_selection(self, query, user):
        """Обработка выбора интереса"""
        interest = query.data.replace('interest_', '')
        
        if interest in user.interests:
            user.interests.remove(interest)
        else:
            if len(user.interests) >= 5 and not user.premium:
                await query.answer("🔒 Максимум 5 интересов для обычных пользователей")
                return
            user.interests.append(interest)
        
        await self.user_service.update_user(user)
        await query.message.edit_reply_markup(
            reply_markup=self.keyboards.get_interests_keyboard(user.interests)
        )
        await query.answer()

    async def _handle_interest_reset(self, query, user):
        """Обработка сброса интересов"""
        user.interests = []
        await self.user_service.update_user(user)
        await query.message.edit_reply_markup(
            reply_markup=self.keyboards.get_interests_keyboard([])
        )
        await query.answer("Интересы сброшены")

    async def _handle_profile_settings(self, query, user):
        """Обработка настроек профиля"""
        # Здесь можно добавить логику настроек профиля
        await query.message.edit_text(
            "*⚙️ Настройки профиля*\n\n"
            "_Выберите действие:_",
            parse_mode='Markdown',
            reply_markup=self.keyboards.get_profile_keyboard()
        )
        await query.answer()

    async def _handle_like(self, query, user):
        """Обработка лайка"""
        target_id = query.data.replace('like_', '')
        target_user = await self.user_service.get_user(target_id)
        
        if target_user:
            target_user.likes += 1
            await self.user_service.update_user(target_user)
            await query.answer("👍 Вы поставили лайк")
        else:
            await query.answer("Пользователь не найден")

    async def _handle_dislike(self, query, user):
        """Обработка дизлайка"""
        target_id = query.data.replace('dislike_', '')
        target_user = await self.user_service.get_user(target_id)
        
        if target_user:
            target_user.dislikes += 1
            await self.user_service.update_user(target_user)
            await query.answer("👎 Вы поставили дизлайк")
        else:
            await query.answer("Пользователь не найден")