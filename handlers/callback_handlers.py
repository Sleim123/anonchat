from telegram import Update
from telegram.ext import ContextTypes
from services.user_service import UserService
from utils.keyboards import Keyboards
import logging

class CallbackHandler:
    def __init__(self, user_service: UserService):
        self.user_service = user_service
        self.keyboards = Keyboards()

    async def handle_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Основной обработчик всех callback запросов"""
        query = update.callback_query
        if not query:
            return

        try:
            user_id = str(query.from_user.id)
            user = await self.user_service.get_user(user_id)
            
            if not user:
                await query.answer("Ошибка: пользователь не найден")
                return

            callback_data = query.data
            
            # Маршрутизация callback запросов
            if callback_data.startswith("interest_"):
                await self._handle_interest_selection(query, user)
            elif callback_data == "reset_interests":
                await self._handle_interests_reset(query, user)
            elif callback_data == "profile_settings":
                await self._handle_profile_settings(query, user)
            elif callback_data.startswith("set_gender_"):
                await self._handle_gender_setting(query, user)
            elif callback_data == "delete_gender":
                await self._handle_gender_deletion(query, user)
            elif callback_data == "back_to_profile":
                await self._handle_back_to_profile(query, user)
            elif callback_data.startswith(("like_", "dislike_")):
                await self._handle_rating(query, user)
            else:
                await query.answer("Неизвестный запрос")

        except Exception as e:
            logging.error(f"Error in callback handling: {e}")
            await query.answer("Произошла ошибка при обработке запроса")

    async def _handle_interest_selection(self, query, user):
        """Обработка выбора интереса"""
        interest = query.data.replace("interest_", "")
        
        if interest in user.interests:
            user.interests.remove(interest)
        else:
            if len(user.interests) >= 5:  # Ограничение на количество интересов
                await query.answer("Максимум 5 интересов!")
                return
            user.interests.append(interest)

        await self.user_service.update_user(user)
        await query.edit_message_reply_markup(
            reply_markup=self.keyboards.get_interests_keyboard(user.interests)
        )
        await query.answer()

    async def _handle_interests_reset(self, query, user):
        """Обработка сброса интересов"""
        if not user.interests:
            await query.answer("У вас нет выбранных интересов")
            return

        user.interests = []
        await self.user_service.update_user(user)
        
        await query.edit_message_reply_markup(
            reply_markup=self.keyboards.get_interests_keyboard([])
        )
        await query.answer("Интересы сброшены")

    async def _handle_profile_settings(self, query, user):
        """Обработка перехода в настройки профиля"""
        current_gender = user.gender
        gender_text = {
            "m": "мужской",
            "w": "женский",
            None: "не указан"
        }[current_gender]

        message_text = (
            "*💅 Настройки пола*\n\n"
            "_Укажите свой пол для более точного поиска собеседников._\n\n"
            f"_Текущий пол: {gender_text}_"
        )

        await query.edit_message_text(
            text=message_text,
            parse_mode='Markdown',
            reply_markup=self.keyboards.get_profile_keyboard()
        )
        await query.answer()

    async def _handle_gender_setting(self, query, user):
        """Обработка установки пола"""
        gender = query.data.replace("set_gender_", "")
        if gender not in ["m", "w"]:
            await query.answer("Некорректный пол")
            return

        user.gender = gender
        await self.user_service.update_user(user)

        gender_text = "мужской" if gender == "m" else "женский"
        await query.answer(f"Установлен {gender_text} пол")
        
        # Обновляем сообщение с профилем
        await self._update_profile_message(query, user)

    async def _handle_gender_deletion(self, query, user):
        """Обработка удаления пола"""
        if not user.gender:
            await query.answer("Пол уже не указан")
            return

        user.gender = None
        await self.user_service.update_user(user)
        await query.answer("Пол удален")
        
        # Обновляем сообщение с профилем
        await self._update_profile_message(query, user)

    async def _handle_back_to_profile(self, query, user):
        """Обработка возврата к профилю"""
        await self._update_profile_message(query, user)
        await query.answer()

    async def _handle_rating(self, query, user):
        """Обработка оценки собеседника"""
        action, rated_user_id = query.data.split('_')
        rated_user = await self.user_service.get_user(rated_user_id)

        if not rated_user:
            await query.answer("Пользователь не найден")
            return

        if action == "like":
            rated_user.likes += 1
        else:  # dislike
            rated_user.dislikes += 1

        await self.user_service.update_user(rated_user)
        await query.edit_message_text(
            "_Спасибо за отзыв!_",
            parse_mode='Markdown'
        )
        await query.answer()

    async def _update_profile_message(self, query, user):
        """Обновление сообщения профиля"""
        gender_text = {
            "m": "мужской",
            "w": "женский",
            None: "не указан"
        }[user.gender]

        profile_text = (
            f"*👤 Ваш профиль*\n\n"
            f"🆔 ID: `{user.id}`\n"
            f"👫 Пол: {gender_text}\n"
            f"💬 Количество чатов: {user.chats_count}\n"
            f"👍 Лайков: {user.likes}\n"
            f"👎 Дизлайков: {user.dislikes}\n"
            f"👑 Premium: {'Да' if user.premium else 'Нет'}\n\n"
            f"📝 Интересы: {', '.join(user.interests) if user.interests else 'не указаны'}"
        )

        await query.edit_message_text(
            text=profile_text,
            parse_mode='Markdown',
            reply_markup=self.keyboards.get_profile_keyboard()
        )