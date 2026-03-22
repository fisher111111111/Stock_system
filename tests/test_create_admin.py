# tests/create_admin.py
import sys
import os
import bcrypt  # 🔥 Используем bcrypt, как в приложении!
import pytest
from sqlalchemy import text, inspect

project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from ..stock_system import app, db

with app.app_context():
    try:
        # Данные пользователя
        first_name = 'admin'
        last_name = 'Admin'
        password = 'admin'
        role = 'Manager'

        # 1. 🔥 Хешируем пароль через bcrypt (как в приложении!)
        password_bytes = password.encode('utf-8')
        hashed_pw = bcrypt.hashpw(password_bytes, bcrypt.gensalt())
        print(f"🔐 Хэш bcrypt: {hashed_pw[:60]}...")
        print(f"🔐 Длина хэша: {len(hashed_pw)} байт")

        # Проверяем структуру таблицы
        inspector = inspect(db.engine)
        columns = inspector.get_columns('users')
        print(f"\n📋 Колонки таблицы 'users':")
        for col in columns:
            print(f"   - {col['name']}: {col['type']}")

        # Проверяем, есть ли уже пользователь
        existing = db.session.execute(
            text("SELECT * FROM users WHERE first_name = :first_name"),
            {"first_name": first_name}
        ).fetchone()

        if existing:
            print(f"\n⚠️ Пользователь с first_name='{first_name}' уже существует!")
            print(f"   Текущий хэш: {existing[3][:50] if existing[3] else None}...")
        else:
            # 2. Вставляем пользователя с bcrypt-хэшем
            db.session.execute(
                text("""
                    INSERT INTO users (first_name, last_name, password, role) 
                    VALUES (:first_name, :last_name, :password, :role)
                """),
                {
                    "first_name": first_name,
                    "last_name": last_name,
                    "password": hashed_pw,  # 🔥 bcrypt-хэш в байтах
                    "role": role
                }
            )
            db.session.commit()
            print(f"\n✅ Пользователь создан успешно!")
            print(f"   First Name: {first_name}")
            print(f"   Last Name: {last_name}")
            print(f"   Password: {password}")
            print(f"   Role: {role}")
            print(f"\n💡 При входе используйте first_name='{first_name}' как логин")

        # 3. 🔍 Тест: проверяем, что bcrypt может верифицировать наш хэш
        print(f"\n🧪 Тест верификации пароля...")
        if bcrypt.checkpw(password_bytes, hashed_pw):
            print("✅ bcrypt.checkpw() подтверждает: пароль верный!")
        else:
            print("❌ Ошибка: bcrypt не принимает хэш!")

    except ImportError:
        print("❌ Ошибка: модуль bcrypt не установлен!")
        print("💡 Установите: pip install bcrypt")
    except Exception as e:
        print(f"\n❌ Ошибка: {type(e).__name__}: {e}")