import telebot
from telebot.types import ReplyKeyboardMarkup, KeyboardButton
from openai import OpenAI
import json
import time
import csv
import os
import string
from datetime import datetime
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton

# =========================
# 🔐 КЛЮЧИ
# =========================
TELEGRAM_TOKEN = open("token.txt").read().strip()
OPENAI_KEY = open("openai_key.txt").read().strip()

bot = telebot.TeleBot(TELEGRAM_TOKEN)
client = OpenAI(api_key=OPENAI_KEY)

# =========================
# 🎮 СОСТОЯНИЕ
# =========================
games = {}

def get_game_key(message):
    return f"{message.chat.id}:{message.from_user.id}"

# =========================
# ⌨️ КНОПКИ
# =========================
def get_keyboard(lang):
    markup = ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add(
        KeyboardButton(f"🔄 {t('start', lang)}"),
        KeyboardButton(t("hint", lang))
    )
    return markup

# =========================
# 📄 проверка города
# =========================

def get_valid_next_city(letter, history, lang):
    result = query_gpt_next_city(letter, history, lang)

    if not result:
        return None, None

    return result.get("next_city"), result.get("next_city_fact")

# =========================
# 📄 Язык клавиатуры
# =========================
def language_keyboard():
    markup = InlineKeyboardMarkup()
    markup.add(
        InlineKeyboardButton("🇺🇦 Українська", callback_data="lang_uk"),
        InlineKeyboardButton("🇬🇧 English", callback_data="lang_en"),
        InlineKeyboardButton("ru", callback_data="lang_ru"),
    )
    return markup
# =========================
# 📄 ЛОГИ
# =========================
def log_user(user_id, chat_id, name, username, text):
    try:
        file_name = "user_logs.csv"
        file_exists = os.path.isfile(file_name)
        with open(file_name, "a", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            if not file_exists:
                writer.writerow(["user_id", "chat_id", "name", "username", "message", "time"])
            writer.writerow([
                user_id, chat_id, name, username, text,
                datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            ])
            f.flush()
            print("LOGGED:", user_id, text, flush=True)
    except Exception as e:
        print("LOG ERROR:", e, flush=True)

# =========================
# 🔤 ЛОГИКА
# =========================
IGNORE_LETTERS = {
    "ru": ["ь", "ъ", "ы", "й", " "],
    "uk": ["ь", "й", " "],
    "en": [" "]  # в английском почти ничего не игнорим
}

def get_last_letter(city, lang="ru"):
    city = city.lower().strip()
    ignore = set(IGNORE_LETTERS.get(lang, []))

    for letter in reversed(city):
        if letter not in ignore and letter.isalpha():
            return letter

    return None

def normalize(city):
    return city.lower().strip().replace("ё", "е")

def is_duplicate(city, history):
    city = normalize(city)

    lower_history = [
        normalize(item["user"])
        for item in history
    ] + [
        normalize(item["bot"])
        for item in history
    ]

    return city in lower_history

# =========================
# 🛡️ SAFE JSON
# =========================
def safe_parse_json(raw):
    try:
        raw = raw.strip()
        if not raw.startswith("{"):
            start = raw.find("{")
            end = raw.rfind("}")
            if start != -1 and end != -1:
                raw = raw[start:end+1]
        return json.loads(raw)
    except Exception as e:
        print("JSON ERROR:", repr(e))
        print("RAW:", repr(raw))
        return None

# =========================
# Translate
# =========================
def t(key, lang):
    return TRANSLATIONS.get(lang, TRANSLATIONS["en"]).get(
        key,
        TRANSLATIONS["en"].get(key, key)
    )

TRANSLATIONS = {
    "ru": {
        "start": "Старт",
        "hint": "💡 Подсказка",
        "enter_city": "Напиши любой город",
        "duplicate": "Этот город уже был",
        "error": "Что-то пошло не так, попробуй ещё раз",
        "choose_language_first": "Сначала выбери язык через /start 🌍",
        "accepted": "🔥 Принято!",
        "reset_done": "Начинаем заново! 🔄",
        "ai_error": "Ошибка ИИ 😢 Попробуй ещё раз.",
        "hint_start": "💡 Подсказка:\nНапиши любой город, и игра начнётся 🌍",
        "hint_try": "💡 Подсказка:\nПопробуй: {city}",
        "hint_letter": "На букву: {letter}"
    },
    "uk": {
        "start": "Старт",
        "hint": "💡 Підказка",
        "enter_city": "Напиши будь-яке місто",
        "duplicate": "Це місто вже було",
        "error": "Щось пішло не так, спробуй ще раз",
        "choose_language_first": "Спочатку обери мову через /start 🌍",
        "accepted": "🔥 Прийнято!",
        "reset_done": "Починаємо заново! 🔄",
        "ai_error": "Помилка ШІ 😢 Спробуй ще раз.",
        "hint_start": "💡 Підказка:\nНапиши будь-яке місто, і гра почнеться 🌍",
        "hint_try": "💡 Підказка:\nСпробуй: {city}",
        "hint_letter": "На букву: {letter}"
    },
    "en": {
        "start": "Start",
        "hint": "💡 Hint",
        "enter_city": "Enter any city",
        "duplicate": "This city was already used",
        "error": "Something went wrong, try again",
        "choose_language_first": "Please choose a language first via /start 🌍",
        "accepted": "🔥 Accepted!",
        "reset_done": "Starting over! 🔄",
        "ai_error": "AI error 😢 Please try again.",
        "hint_start": "💡 Hint:\nEnter any city to start the game 🌍",
        "hint_try": "💡 Hint:\nTry: {city}",
        "hint_letter": "For the letter: {letter}"
    }
}


# =========================
# 🤖 GPT
# =========================
    
PROMPTS = {
    "ru": {
        "next_city": """
Ты играешь в игру "Города".

Правила:
1. Назови город на букву "{letter}"
2. Не повторяй города из списка
3. Дай короткий факт

История:
{history}

Ответ ТОЛЬКО JSON:

{{
  "next_city": "...",
  "next_city_fact": "..."
}}
""",

        "city_check": """
Ты дружелюбный Telegram-бот.
Пользователь написал город: "{city}"

Проверь:
1. Существует ли город
2. Исправь ошибки
3. Дай короткий факт

Верни ТОЛЬКО JSON:

{{
  "valid": true,
  "correct_name": "...",
  "fact": "..."
}}
""",

        "error_letter": """
Игрок ошибся.
Скажи, что город должен начинаться на "{letter}".
Коротко и дружелюбно.
""",

        "duplicate": """
Игрок повторил город "{city}".
Скажи, что он уже был, и попроси другой.
"""
    },

    "uk": {
        
        "city_check": """
Ти дружній Telegram-бот.
Користувач написав місто: "{city}"

Перевір:
1. Чи існує місто
2. Виправ написання
3. Дай короткий факт

Поверни ТІЛЬКИ JSON:

{{
  "valid": true,
  "correct_name": "...",
  "fact": "..."
}}
""",

        "error_letter": """
Гравець помилився.
Скажи, що місто має починатися на "{letter}".
Коротко і дружньо.
""",

        "duplicate": """
Гравець повторив місто "{city}".
Скажи, що воно вже було, і попроси інше.
"""
    },

    "en": {
        "next_city": """
You are playing the "Cities" game.

Rules:
1. Say a city starting with "{letter}"
2. Do not repeat cities from the list
3. Give a short fact

History:
{history}

Return ONLY JSON:

{{
  "next_city": "...",
  "next_city_fact": "..."
}}
""",

        "city_check": """
You are a friendly Telegram bot.
User entered city: "{city}"

Check:
1. Does the city exist
2. Fix spelling
3. Give short fact

Return ONLY JSON:

{{
  "valid": true,
  "correct_name": "...",
  "fact": "..."
}}
""",

        "error_letter": """
User made a mistake.
Tell them the city must start with "{letter}".
Short and friendly.
""",

        "duplicate": """
User repeated city "{city}".
Tell them it was already used and ask for another.
"""
    }
}


def query_gpt_city_check(user_city, lang):
    prompt = PROMPTS[lang]["city_check"].format(city=user_city)

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "Return ONLY valid JSON. No explanations."},
                {"role": "user", "content": prompt}
            ],
            temperature=0
        )

        raw = response.choices[0].message.content
        return safe_parse_json(raw)

    except Exception as e:
        print("GPT CHECK ERROR:", e)
        return None
    

def query_gpt_next_city(letter, history, lang):
    history_list = [item["user"] for item in history] + [item["bot"] for item in history]

    prompt = PROMPTS[lang]["next_city"].format(
        letter=letter.upper(),
        history=history_list
    )

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
    {"role": "system", "content": "Return ONLY valid JSON."},
    {"role": "user", "content": prompt}
],
            temperature=0.7
        )

        return safe_parse_json(response.choices[0].message.content)

    except Exception as e:
        print("GPT NEXT ERROR:", e)
        return None
    
# =========================
# 🤖 ОШИБКА БУКВЫ
# =========================
def generate_error_message(letter, lang):
    try:
        prompt = PROMPTS[lang]["error_letter"].format(letter=letter.upper())

        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "system", "content": prompt}],
            temperature=0.8
        )

        return response.choices[0].message.content.strip()

    except:
        return f"{t('error', lang)}"

# =========================
# 🤖 ОБРАБОТКА ПОВТОРА
# =========================

def handle_duplicate_city(city, history, lang):
    try:
        prompt = PROMPTS[lang]["duplicate"].format(city=city)

        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "system", "content": prompt}],
            temperature=0
        )

        return response.choices[0].message.content.strip()

    except:
        return t("duplicate", lang)

# =========================
# ▶️ START
# =========================
@bot.message_handler(commands=['start'])
def start(message):
    key = get_game_key(message)

    # создаем или сбрасываем игру
    games[key] = {
        "history": [],
        "processing": False,
        "language": None
    }

    # показываем выбор языка
    bot.send_message(
        message.chat.id,
        "🌍 Обери мову / Choose language:",
        reply_markup=language_keyboard()
    )

# =========================
# 💬 HANDLE
# =========================

@bot.callback_query_handler(func=lambda call: call.data.startswith("lang_"))
def set_language(call):
    key = f"{call.message.chat.id}:{call.from_user.id}"

    if key not in games:
        games[key] = {"history": [], "processing": False, "language": None}

    lang = call.data.split("_")[1]
    games[key]["language"] = lang

    # удаляем кнопки (редактируем сообщение)
    bot.edit_message_text(
        "✅ Мову обрано! Тепер напиши місто 🌍",
        chat_id=call.message.chat.id,
        message_id=call.message.message_id
    )

    bot.send_message(
        call.message.chat.id,
        t("enter_city", lang),
        reply_markup=get_keyboard(lang)
    )

@bot.message_handler(func=lambda m: True)
def handle_message(message):
    key = get_game_key(message)
    if key not in games:
        games[key] = {"history": [], "processing": False, "language": None}

    game = games[key]
    text = message.text.strip()

    # 🔄 reset / start — независимо от выбранного языка
    RESET_BUTTONS = ["🔄 Старт", "🔄 Старт", "🔄 Start"]  # ru, uk, en
    if text in RESET_BUTTONS:
        start(message)  # сразу показываем выбор языка
        return  # выходим, чтобы не шли дальше проверки

    # ❗ проверка языка — для всех остальных сообщений
    lang = game.get("language")
    if not lang:
        bot.send_message(
            message.chat.id,
            "🌍 Обери мову / Choose language:",
            reply_markup=language_keyboard()
        )
        return

    # если игра в процессе — игнорируем новые сообщения
    if game["processing"]:
        return
    game["processing"] = True

    try:
        history = game["history"]
        user_city = text.title()  # нормализуем введённый город

        # 💡 hint
        if text == t("hint", lang):
            if not history:
                bot.reply_to(
                    message,
                    t("hint_start", lang),  # ✅ теперь перевод
                    reply_markup=get_keyboard(lang)
                )
                return

            last_bot_city = history[-1]["bot"] if history[-1]["bot"] else history[-1]["user"]
            letter = get_last_letter(last_bot_city)
            hint_city, _ = get_valid_next_city(letter, history, lang)

            if hint_city:
                bot.reply_to(
                    message,
                    t("hint_try", lang).format(city=hint_city),  # ✅ мультиязычный текст
                    reply_markup=get_keyboard(lang)
                )
            else:
                bot.reply_to(
                    message,
                    t("hint_letter", lang).format(letter=letter.upper()),  # ✅ мультиязычный текст
                    reply_markup=get_keyboard(lang)
                )
            return

        # 🔹 duplicate check
        if is_duplicate(user_city, history):
            ai_text = handle_duplicate_city(user_city, history, lang)
            bot.reply_to(message, ai_text, reply_markup=get_keyboard(lang))
            return

        # 🔹 проверка первой буквы
        if history:
            last_bot_city = history[-1]["bot"] if history[-1]["bot"] else history[-1]["user"]
            required_letter = get_last_letter(last_bot_city, lang)
            if not user_city or normalize(user_city)[0] != required_letter:
                # используем мультиязычный текст для ошибки
                error_msg = generate_error_message(required_letter, lang)
                bot.reply_to(message, error_msg, reply_markup=get_keyboard(lang))
                return

        # 🔹 проверка существования города + факт
        city_check = query_gpt_city_check(user_city, lang)
        if not city_check or not city_check.get("valid"):
            error_msg = city_check.get("message_to_user") if city_check and "message_to_user" in city_check else t("error", lang)
            bot.reply_to(message, error_msg, reply_markup=get_keyboard(lang))
            return

        # 🔹 нормализованное имя города
        correct_city = city_check.get("correct_name", user_city)

        # 🔹 повторная проверка
        if is_duplicate(correct_city, history):
            ai_text = handle_duplicate_city(correct_city, history, lang)
            bot.reply_to(message, ai_text, reply_markup=get_keyboard(lang))
            return

        user_city = correct_city
        user_fact = city_check["fact"]
        last_letter = get_last_letter(user_city)

        # 🔹 следующий город ИИ
        bot_city, bot_fact = get_valid_next_city(
            last_letter,
            history + [{"user": user_city, "bot": ""}],
            lang
        )

        if not bot_city:
            bot.reply_to(message, t("ai_error", lang))
            return

        # ✅ обновление истории
        game["history"].append({
            "user": user_city,
            "bot": bot_city or "",
            "user_fact": user_fact,
            "bot_fact": bot_fact or ""
        })

        # ✅ ответ пользователю
        bot.reply_to(
            message,
            f"{t('accepted', lang)}\n\n"
            f"📚 {user_fact}\n"
            f"➡️ {bot_city}\n"
            f"📖 {bot_fact}",
            reply_markup=get_keyboard(lang)
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
