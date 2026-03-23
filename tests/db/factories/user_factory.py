# tests/factories/user_factory.py
import uuid
import bcrypt
from typing import Optional, Union

from Stock_Management_System.db.sqlserver_base import SqlServerBase


class UserFactory:
    """Фабрика для создания тестовых данных пользователя."""

    DEFAULT_PASSWORD_HASH = "$2b$12$L200Ig7ZerAgLZOBmK.3quk2kC0grMxMUUbrpKnpA.Z.8LY8DFcRC"

    @staticmethod
    def build(
            first_name: Optional[str] = None,
            last_name: Optional[str] = None,
            password: Optional[Union[str, bytes]] = None,
            role: Optional[str] = None,
            **overrides
    ) -> dict:
        """Создать словарь данных пользователя с УНИКАЛЬНЫМИ именами."""
        unique_suffix = uuid.uuid4().hex[:8]

        base = {
            "first_name": first_name or f"Test_{unique_suffix}",
            "last_name": last_name or f"Test_{unique_suffix}",
            "password": password or UserFactory.DEFAULT_PASSWORD_HASH,
            "role": role or "Employee",
        }
        base.update(overrides)
        return base

    @staticmethod
    def hash_password(plain_password: str) -> str:
        """Создать bcrypt-хэш пароля как строку."""
        salt = bcrypt.gensalt(rounds=12)
        hashed = bcrypt.hashpw(plain_password.encode('utf-8'), salt)
        return hashed.decode('utf-8')

    @staticmethod
    def encode_password(password: Union[str, bytes]) -> bytes:
        """Конвертировать пароль в bytes для VARBINARY колонки."""
        if isinstance(password, bytes):
            return password
        return password.encode('utf-8')

    @staticmethod
    def decode_password(password: Union[str, bytes]) -> str:
        """Конвертировать пароль из bytes в строку."""
        if isinstance(password, bytes):
            return password.decode('utf-8')
        return password

    @staticmethod
    def create(db: SqlServerBase, **overrides) -> dict:
        """Создать и вставить пользователя в БД, вернуть данные с ID."""
        data = UserFactory.build(**overrides)

        # ✅ Конвертируем пароль в bytes для VARBINARY колонки
        if "password" in data and isinstance(data["password"], str):
            data["password"] = UserFactory.encode_password(data["password"])

        db._insert(table="users", data=data)

        result = db._select(
            fields=["*"],
            from_table="users",
            where={"first_name": data["first_name"], "last_name": data["last_name"]}
        )
        return result[0] if result else None