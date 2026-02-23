PROMPTS = {
    "ru": {
        "city_check": """
Ты дружелюбный Telegram-бот.
Пользователь написал город: "{city}"

Проверь:
1. Существует ли город
2. Исправь ошибки
3. Дай короткий факт

Ответ JSON:
{{
  "valid": true,
  "correct_name": "...",
  "fact": "..."
}}
"""
    },

    "uk": {
        "city_check": """
Ти дружній Telegram-бот.
Користувач написав місто: "{city}"

Перевір:
1. Чи існує місто
2. Виправ помилки
3. Дай короткий факт

Відповідь JSON:
{{
  "valid": true,
  "correct_name": "...",
  "fact": "..."
}}
"""
    },

    "en": {
        "city_check": """
You are a friendly Telegram bot.
User entered city: "{city}"

Check:
1. Does city exist
2. Fix spelling
3. Give short fact

Return JSON:
{{
  "valid": true,
  "correct_name": "...",
  "fact": "..."
}}
"""
    }
}
lang = "uk"
print(PROMPTS[lang]["city_check"])