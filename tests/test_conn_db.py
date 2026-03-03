# tests/test_conn_db.py
import sys
import os
from sqlalchemy import text, inspect

# Добавляем корень проекта в путь
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from stock_system import app, db


def test_connection():
    with app.app_context():
        try:
            # ✅ Используем text() для SQL-запросов
            db.session.execute(text("SELECT 1"))
            print("✅ Подключение к БД успешно!")

            # Список таблиц
            inspector = inspect(db.engine)
            tables = inspector.get_table_names()
            print(f"📋 Таблицы: {tables}")

            # ✅ Проверяем, что таблицы существуют
            assert len(tables) > 0, "В базе данных нет таблиц"

            # Поиск таблицы пользователей
            user_table_found = False
            for table in tables:
                if 'user' in table.lower():
                    user_table_found = True
                    count = db.session.execute(text(f"SELECT COUNT(*) FROM {table}")).scalar()
                    print(f"👤 В таблице '{table}': {count} записей")

                    if count > 0:
                        users = db.session.execute(text(f"SELECT * FROM {table}")).fetchall()
                        for u in users:
                            print(f"   {u}")

            # ✅ Проверяем, что таблица пользователей найдена
            assert user_table_found, "Таблица пользователей не найдена"

        except Exception as e:
            # ✅ При ошибке тест упадет с сообщением
            assert False, f"❌ Ошибка: {type(e).__name__}: {e}"

if __name__ == "__main__":
    test_connection()