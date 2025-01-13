from telegram import KeyboardButton, ReplyKeyboardMarkup, InlineKeyboardButton, InlineKeyboardMarkup

class Keyboards:
    @staticmethod
    def get_main_keyboard(is_searching=False):
        if is_searching:
            buttons = [[KeyboardButton("❌ Остановить поиск")]]
        else:
            buttons = [
                [KeyboardButton("🔎 Поиск собеседника")],
                [KeyboardButton("🎭 Поиск по полу")],
                [KeyboardButton("📙 Интересы")],
                [KeyboardButton("💼 Профиль")]
            ]
        return ReplyKeyboardMarkup(buttons, resize_keyboard=True)

    @staticmethod
    def get_gender_search_keyboard():
        buttons = [
            [KeyboardButton("👨‍🦰 Поиск М"), KeyboardButton("👩‍🦱 Поиск Д")],
            [KeyboardButton("◀️ Вернуться назад")]
        ]
        return ReplyKeyboardMarkup(buttons, resize_keyboard=True)

    @staticmethod
    def get_interests_keyboard(selected_interests=[]):
        interests = ["Знакомства", "Мемы", "Спорт", "Путешествия", 
                    "Кино", "Книги", "Одиночество", "Игры"]
        buttons = []
        
        for i in range(0, len(interests), 2):
            row = []
            for j in range(2):
                if i + j < len(interests):
                    interest = interests[i + j]
                    text = f"✅ {interest}" if interest in selected_interests else interest
                    row.append(InlineKeyboardButton(
                        text, 
                        callback_data=f"interest_{interest}"
                    ))
            buttons.append(row)
        
        buttons.append([InlineKeyboardButton(
            "❌ Сбросить интересы", 
            callback_data="reset_interests"
        )])
        
        return InlineKeyboardMarkup(buttons)

    @staticmethod
    def get_profile_keyboard():
        buttons = [[InlineKeyboardButton("Настройки пола", callback_data="profile_settings")]]
        return InlineKeyboardMarkup(buttons)

    @staticmethod
    def get_rating_keyboard(user_id: str):
        buttons = [[
            InlineKeyboardButton("👍", callback_data=f"like_{user_id}"),
            InlineKeyboardButton("👎", callback_data=f"dislike_{user_id}")
        ]]
        return InlineKeyboardMarkup(buttons)