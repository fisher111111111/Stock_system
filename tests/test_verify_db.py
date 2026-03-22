# tests/test_verify_db.py
import sys, os

import pytest
from sqlalchemy import text

project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from ..stock_system import app, db

with app.app_context():
    result = db.session.execute(text("SELECT first_name, password FROM users")).fetchall()
    print(f"👤 Пользователи в БД:")
    for first_name, pw_hash in result:
        # Проверяем формат хэша
        if isinstance(pw_hash, bytes):
            pw_hash = pw_hash.decode('utf-8', errors='ignore')
        prefix = pw_hash[:10] if pw_hash else None
        print(f"   - {first_name}: хэш начинается с '{prefix}...'")
        if prefix and prefix.startswith('$2b$') or prefix.startswith('$2a$'):
            print(f"     ✅ Формат bcrypt — всё верно!")
        elif prefix and prefix.startswith('scrypt:'):
            print(f"     ❌ Формат scrypt — НЕ подходит для этого приложения!")
        else:
            print(f"     ⚠️ Неизвестный формат хэша")