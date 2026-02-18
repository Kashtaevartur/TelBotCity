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
# 🎮 ИГРЫ (НОВАЯ СТРУКТУРА)
# =========================
games = {}

def get_game_key(message):
    return f"{message.chat.id}:{message.from_user.id}"

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
def log_user(user_id, chat_id, name, username, text):
    try:
        file_exists = os.path.isfile("user_logs.csv")

        with open("user_logs.csv", "a", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)

            if not file_exists:
                writer.writerow([
                    "user_id", "chat_id", "name",
                    "username", "message", "time"
                ])

            writer.writerow([
                user_id,
                chat_id,
                name,
                username,
                text,
                datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            ])

    except Exception as e:
        print("LOG ERROR:", e)

# =========================
# 🔤 ЛОГИКА БУКВ
# =========================
def get_last_letter(city):
    city = city.lower()
    for letter in reversed(city):
        if letter not in ["ь", "ъ", "ы", "й"]:
            return letter
    return city[-1]


def is_valid_letter(user_city, history):
    if not history:
        return True

    last_city = history[-1]
    required = get_last_letter(last_city)
    return user_city[0].lower() == required


def is_duplicate(city, history):
    return city.lower() in [c.lower() for c in history]

# =========================
# 🤖 GPT
# =========================
INSTRUCTION = """
Мы играем в игру "Города".

История: {history}
Город пользователя: {user_city}

Ответ строго JSON.
"""

def query_gpt(user_city, history):
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "system",
                    "content": INSTRUCTION.format(
                        history=", ".join(history) if history else "нет",
                        user_city=user_city
                    )
                }
            ],
            temperature=0.7
        )

        raw = response.choices[0].message.content.strip()
        print("GPT RAW:", raw)

        try:
            return json.loads(raw)
        except:
            print("JSON PARSE ERROR:", raw)
            return None

    except Exception as e:
        print("GPT ERROR:", e)
        return None

# =========================
# ▶️ START
# =========================
@bot.message_handler(commands=['start'])
def start(message):
    key = get_game_key(message)

    games[key] = {
        "history": [],
        "processing": False
    }

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
    key = get_game_key(message)
    text = message.text.strip()

    log_user(
        message.from_user.id,
        message.chat.id,
        message.from_user.first_name,
        message.from_user.username,
        text
    )

    # создаём игру
    if key not in games:
        games[key] = {
            "history": [],
            "processing": False
        }

    game = games[key]

    # 🔒 защита от двойных запросов
    if game["processing"]:
        return

    game["processing"] = True

    try:
        history = game["history"]

        # 🔄 reset
        if text == "🔄 Спробуй заново":
            game["history"] = []
            bot.reply_to(message, "Починаємо заново!", reply_markup=keyboard)
            return

        # 💡 подсказка
        if text == "💡 Підказка":
            if history:
                letter = get_last_letter(history[-1])
                bot.reply_to(message, f"На букву: {letter.upper()}", reply_markup=keyboard)
            else:
                bot.reply_to(message, "Напиши будь-яке місто", reply_markup=keyboard)
            return

        user_city = text.title()

        # ❌ проверки
        if is_duplicate(user_city, history):
            bot.reply_to(message, "Этот город уже был 😏", reply_markup=keyboard)
            return

        if not is_valid_letter(user_city, history):
            bot.reply_to(message, "Нужно на правильную букву 😏", reply_markup=keyboard)
            return

        # 🤖 GPT
        ai_data = query_gpt(user_city, history)

        if not ai_data:
            bot.reply_to(message, "Помилка ІІ 😢")
            return

        if not ai_data.get("valid"):
            bot.reply_to(message, ai_data.get("message_to_user"), reply_markup=keyboard)
            return

        # ✅ атомарное обновление
        game["history"].extend([
            user_city,
            ai_data["next_city"]
        ])

        # ответ
        bot.reply_to(
            message,
            f"Принято! 🔥\n\n"
            f"📚 {ai_data['fact']}\n"
            f"➡️ {ai_data['next_city']}\n"
            f"📖 {ai_data['next_city_fact']}",
            reply_markup=keyboard
        )

    finally:
        game["processing"] = False


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
