import openai
import json
from db import add_city, get_history, reset_history
from temp_storage import save_ai_response, get_all_responses, clear_temp_file

openai.api_key = "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"

def query_gpt():
    history = [c.title() for c in get_history()]  # берем всю историю
    last_city = history[-1]  # последний введенный город

    prompt = f"""
Мы играем в игру "Города".
Пользователь написал город: "{last_city}".
История использованных городов: {', '.join(history)}.

Правила:
1. Проверь, существует ли город и не повторяется ли он.
2. Дай короткий интересный факт о городе (1-2 предложения).
3. Предложи следующий город на последнюю букву пользователя.
4. Постарайся писать разнообразно, чтобы ответы были не шаблонными.

Ответ в JSON формате:
{{
  "message_to_user": "...",
  "valid": true/false,
  "next_city": "...",
  "fact": "..."
}}
"""

    client = openai.OpenAI(api_key=openai.api_key)
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.6
    )

    raw_text = response.choices[0].message.content
    print("Сырой ответ GPT:", raw_text)

    try:
        data = json.loads(raw_text)
        return data
    except json.JSONDecodeError:
        # пробуем вытянуть JSON из текста
        import re
        match = re.search(r"\{.*\}", raw_text, re.DOTALL)
        if match:
            try:
                data = json.loads(match.group())
                return data
            except:
                pass
        return None

# =========================
# Тестовая игра в терминале
# =========================
def main():
    print("=== Игра 'Города' с ИИ (тестовый режим) ===")
    
    while True:
        user_city = input("Введите город (или 'reset' для новой игры, 'exit' для выхода): ").strip()
        
        if user_city.lower() == "exit":
            print("Выход из игры...")
            break
        if user_city.lower() == "reset":
            reset_history()
            clear_temp_file()
            print("История очищена. Начинаем новую игру!")
            continue
        
        # Сначала добавляем город пользователя в базу
        add_city(user_city.title(), "user")

        # Запрос к GPT с историей
        ai_data = query_gpt()
        if not ai_data:
            print("ИИ не ответил корректно. Попробуйте снова.")
            continue

        # Сохраняем ответ ИИ во временный JSON
        save_ai_response(ai_data)

        # Сохраняем ход ИИ в базу
        if ai_data.get("next_city"):
            add_city(ai_data["next_city"].title(), "ai")

        # Выводим пользователю
        print("\nИИ отвечает:")
        print(ai_data.get("message_to_user"))
        print(f"Факт: {ai_data.get('fact')}")
        print(f"Следующий город (ИИ): {ai_data.get('next_city')}")
        print("-" * 40)

if __name__ == "__main__":
    main()