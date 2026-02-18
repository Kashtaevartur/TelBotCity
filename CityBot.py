import telebot
from telebot.types import ReplyKeyboardMarkup, KeyboardButton
from openai import OpenAI
import json
import time
import csv
import os
from datetime import datetime

# =========================
# 🔐 КЛЮЧИ
# =========================
TELEGRAM_TOKEN = open("token.txt").read().strip()
OPENAI_KEY = open("openai_key.txt").read().strip()

bot = telebot.TeleBot(TELEGRAM_TOKEN)
client = OpenAI(api_key=OPENAI_KEY)

bot.delete_webhook()

# =========================
# 🧠 ИСТОРИЯ
# =========================
history = []

# =========================
# ⌨️ КНОПКИ
# =========================
keyboard = ReplyKeyboardMarkup(resize_keyboard=True)
keyboard.add(
    KeyboardButton("🔄 Спробуй заново"),
    KeyboardButton("💡 Підказка")
)

# =========================
# 📄 ЛОГИ
# =========================
def log_user(user_id, name, username, text):
    try:
        file_exists = os.path.isfile("user_logs.csv")

        with open("user_logs.csv", "a", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)

            if not file_exists:
                writer.writerow(["user_id", "name", "username", "message", "time"])

            writer.writerow([
                user_id,
                name,
                username,
                text,
                datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            ])

        print("LOG OK")

    except Exception as e:
        print("LOG ERROR:", e)

INSTRUCTION = """
Мы играем в игру "Города".

Пользователь написал город: "{user_city}"
История использованных городов: {history}

========================
📌 ПРАВИЛА
========================

1. Город должен существовать
2. Город не должен повторяться
3. Если это НЕ первый ход:
   - возьми ПОСЛЕДНИЙ город из истории
   - определи его последнюю букву

========================
🔤 КАК ОПРЕДЕЛИТЬ БУКВУ
========================

1. Возьми последний город из истории
2. Возьми его последнюю букву
3. Если это одна из букв:
   ь, ъ, ы, й
   → возьми предыдущую букву

Пример:
Киев → в  
Тверь → р  
Одесса → а  

========================
🔎 ПРОВЕРКА
========================

Сравни:
- первую букву города пользователя с последней буквой последнего предпоследнего города в истории

------------------------

❌ ЕСЛИ БУКВА НЕ СОВПАДАЕТ:

Верни:

{
 "message_to_user": "Нужно на правильную букву 😏",
 "valid": false,
 "error_type": "wrong_letter",
 "next_city": "",
 "fact": ""
}

(НЕ вставляй букву в ответ!)

------------------------

🔹 ОПЕЧАТКИ

Если пользователь ошибся в 1-2 буквах:
- исправь город
- считай его валидным
- укажи исправление в corrected_city

------------------------

❌ НЕ СУЩЕСТВУЕТ

{
 "message_to_user": "Я не знаю такого города 😅",
 "valid": false,
 "error_type": "invalid_city",
 "next_city": "",
 "fact": ""
}

------------------------

❌ ПОВТОР

{
 "message_to_user": "Этот город уже был 😏",
 "valid": false,
 "error_type": "duplicate",
 "next_city": "",
 "fact": ""
}

------------------------

✅ ЕСЛИ ВСЁ ОК

1. Дай 1 факт про город пользователя
2. Придумай новый город:
   - на последнюю букву
   - которого нет в истории
3. Дай факт про него

{
 "message_to_user": "Принято! 🔥",
 "valid": true,
 "corrected_city": null,
 "next_city": "...",
 "fact": "...",
 "next_city_fact": "..."
}

========================
⚠️ ВАЖНО
========================

- Отвечай ТОЛЬКО JSON
- Без текста вне JSON
"""



# =========================
# 🤖 GPT
# =========================
def query_gpt(user_input):
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": INSTRUCTION},
                {
                    "role": "user",
                    "content": f"""
История: {', '.join(history) if history else "нет"}

Новое слово: {user_input}
"""
                }
            ],
            temperature=0.7
        )

        raw = response.choices[0].message.content.strip()
        print("GPT RAW:", raw)

        return json.loads(raw)

    except Exception as e:
        print("GPT ERROR:", e)
        return None

# =========================
# ▶️ START
# =========================
@bot.message_handler(commands=['start'])
def start(message):
    global history
    history = []

    print("START")

    log_user(
        message.from_user.id,
        message.from_user.first_name,
        message.from_user.username,
        "/start"
    )

    bot.reply_to(
        message,
        "Вітаю 🌍\nГраємо в міста!\nПиши місто:",
        reply_markup=keyboard
    )

# =========================
# 💬 СООБЩЕНИЯ
# =========================
@bot.message_handler(func=lambda message: True)
def handle(message):
    global history

    text = message.text.strip()
    print("ПРИШЛО:", text)

    log_user(
        message.from_user.id,
        message.from_user.first_name,
        message.from_user.username,
        text
    )

    # 🔄 reset
    if text == "🔄 Спробуй заново":
        history = []
        bot.reply_to(message, "Починаємо заново!", reply_markup=keyboard)
        return

    # 💡 подсказка
    if text == "💡 Підказка":
        if history:
            last = history[-1]
            bot.reply_to(message, f"На букву: {last[-1].upper()}", reply_markup=keyboard)
        else:
            bot.reply_to(message, "Напиши будь-яке місто", reply_markup=keyboard)
        return

    # 🤖 GPT
    ai_data = query_gpt(text.title())

    if not ai_data:
        bot.reply_to(message, "Помилка ІІ 😢")
        return

    # ❌ ошибка
    if not ai_data.get("valid"):
        bot.reply_to(message, ai_data.get("message_to_user"), reply_markup=keyboard)
        return

    # ✅ сохраняем
    history.append(text.title())
    history.append(ai_data["next_city"])

    # лог ответа ИИ
    log_user(
        message.from_user.id,
        "BOT",
        "AI",
        ai_data["next_city"]
    )

    # ответ
    bot.reply_to(
        message,
        f"{ai_data['message_to_user']}\n\n"
        f"📚 {ai_data['fact']}\n"
        f"➡️ {ai_data['next_city']}",
        reply_markup=keyboard
    )

# =========================
# 🚀 ЗАПУСК
# =========================
print("Бот запущен...")

while True:
    try:
        bot.infinity_polling(timeout=60, long_polling_timeout=60)
    except Exception as e:
        print("Polling ERROR:", e)
        time.sleep(5)
