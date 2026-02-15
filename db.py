import sqlite3

# Подключаемся или создаём базу
conn = sqlite3.connect("cities.db", check_same_thread=False)
cursor = conn.cursor()

# Создаём таблицу истории ходов
cursor.execute("""
CREATE TABLE IF NOT EXISTS city_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    city TEXT NOT NULL,
    owner TEXT NOT NULL,  -- 'user' или 'ai'
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
)
""")
conn.commit()

# Функция для добавления города
def add_city(city_name, owner):
    cursor.execute("INSERT INTO city_history (city, owner) VALUES (?, ?)",
                   (city_name.title(), owner))
    conn.commit()

# Функция для получения всей истории
def get_history():
    cursor.execute("SELECT city FROM city_history ORDER BY id")
    return [row[0] for row in cursor.fetchall()]

# Сброс истории (новая игра)
def reset_history():
    cursor.execute("DELETE FROM city_history")
    conn.commit()
