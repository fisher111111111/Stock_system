# Временный скрипт: recreate_db.py
from . import app, db

with app.app_context():
    # Удалить все таблицы
    db.drop_all()
    # Создать заново по обновлённым моделям
    db.create_all()
    print("✅ Таблицы пересозданы!")