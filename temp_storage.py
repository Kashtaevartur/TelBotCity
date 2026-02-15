import json
import os

# Путь к временной базе JSON
TEMP_FILE = "temp_ai_responses.json"

# Сохраняем ответ ИИ
def save_ai_response(data):
    """
    data — словарь с полями:
    {
        "message_to_user": "...",
        "valid": True/False,
        "next_city": "...",
        "fact": "..."
    }
    """
    # Если файла нет, создаём пустой список
    if not os.path.exists(TEMP_FILE):
        with open(TEMP_FILE, "w", encoding="utf-8") as f:
            json.dump([], f, ensure_ascii=False, indent=2)
    
    # Загружаем текущие данные
    with open(TEMP_FILE, "r", encoding="utf-8") as f:
        current_data = json.load(f)

    # Добавляем новый ответ
    current_data.append(data)

    # Сохраняем обратно
    with open(TEMP_FILE, "w", encoding="utf-8") as f:
        json.dump(current_data, f, ensure_ascii=False, indent=2)

# Получаем все временные ответы
def get_all_responses():
    if not os.path.exists(TEMP_FILE):
        return []
    with open(TEMP_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

# Очищаем временный файл
def clear_temp_file():
    if os.path.exists(TEMP_FILE):
        os.remove(TEMP_FILE)
