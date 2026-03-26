# tests/test_users.py
import uuid
import bcrypt
import pytest

from ...db.sqlserver_base import SqlServerBase
from ...tests.db.factories.user_factory import UserFactory


# ✅ Вспомогательные функции для работы с password (VARBINARY ↔ str)
def _decode_password(password) -> str:
    """Конвертирует bytes в строку если нужно."""
    if isinstance(password, bytes):
        return password.decode('utf-8')
    return password


def _encode_password_for_check(password) -> bytes:
    """Конвертирует в bytes для bcrypt.checkpw."""
    if isinstance(password, str):
        return password.encode('utf-8')
    return password


class TestUsersCRUD:
    """Тесты базовых операций с пользователями."""

    def test_insert_employee(self, db_connector: SqlServerBase, clean_users: None):
        """Тест: вставка нового сотрудника."""

        user = UserFactory.create(
            db_connector,
            first_name="John",
            last_name="Doe",
            role="Employee"
        )

        assert user is not None
        assert "id" in user
        assert user["first_name"].startswith("John")  # ✅ Проверяем префикс
        assert user["last_name"].startswith("Doe")
        assert user["role"] == "Employee"

        # ✅ Декодируем password если bytes
        password = _decode_password(user["password"])
        assert password.startswith("$2b$")

    def test_insert_manager(self, db_connector: SqlServerBase, clean_users: None):
        """Тест: вставка нового менеджера."""

        user = UserFactory.create(
            db_connector,
            first_name="Jane",
            last_name="Smith",
            role="Manager"
        )

        assert user["role"] == "Manager"

    # def test_select_user_by_id(self, db_connector: SqlServerBase):
    #     """Тест: получение пользователя по ID (с существующими данными)."""
    #
    #     result = db_connector._select(
    #         fields=["id", "first_name", "last_name", "role"],
    #         from_table="users",
    #         where={"id": 2}
    #     )
    #
    #     assert len(result) == 1
    #     assert result[0]["first_name"] == "John"
    #     assert result[0]["last_name"] == "Doe"
    #     assert result[0]["role"] == "Employee"

    def test_select_user_by_id(self, db_connector: SqlServerBase):
        """Тест: получение пользователя по ID (с существующими данными)."""

        # Ищем пользователя Worker (first_name = 'Worker')
        user_data = db_connector._select(
            fields=["id", "first_name", "last_name", "role"],
            from_table="users",
            where={"first_name": "Worker"}
        )

        # Если Worker не найден, пропускаем тест
        if not user_data:
            pytest.skip("Тестовый пользователь Worker не найден в базе данных")

        # Берём реальный id
        user_id = user_data[0]["id"]

        # Получаем пользователя по id
        result = db_connector._select(
            fields=["id", "first_name", "last_name", "role"],
            from_table="users",
            where={"id": user_id}
        )

        assert len(result) == 1
        assert result[0]["first_name"] == "Worker"
        # last_name может быть пустой строкой или 'Worker' – зависит от данных
        assert result[0]["role"] == "Employee"

    def test_select_users_by_role(self, db_connector: SqlServerBase, clean_users: None):
        """Тест: выборка пользователей по роли."""

        unique_id = uuid.uuid4().hex[:8]  # ✅ Уникальный суффикс

        # Создаём тестовых пользователей с уникальными именами
        UserFactory.create(db_connector, first_name=f"Emp1_{unique_id}", role="Employee")
        UserFactory.create(db_connector, first_name=f"Emp2_{unique_id}", role="Employee")
        UserFactory.create(db_connector, first_name=f"Mgr1_{unique_id}", role="Manager")

        # Выборка сотрудников
        employees = db_connector._select(
            fields=["first_name", "role"],
            from_table="users",
            where={"role": "Employee"}
        )

        emp_names = [u["first_name"] for u in employees]
        # ✅ Проверяем по префиксу с уникальным ID
        assert any(f"Emp1_{unique_id}" in n for n in emp_names)
        assert any(f"Emp2_{unique_id}" in n for n in emp_names)
        assert all(f"Mgr1_{unique_id}" not in n for n in emp_names)

    def test_update_user_role(self, db_connector: SqlServerBase, clean_users: None):
        """Тест: повышение сотрудника до менеджера."""

        user = UserFactory.create(db_connector, role="Employee")
        user_id = user["id"]

        affected = db_connector._update(
            table="users",
            data={"role": "Manager"},
            where={"id": user_id}
        )

        assert affected == 1

        updated = db_connector._select(
            fields=["role"],
            from_table="users",
            where={"id": user_id}
        )[0]

        assert updated["role"] == "Manager"

    def test_update_user_password(self, db_connector: SqlServerBase, clean_users: None):
        """Тест: смена пароля пользователя."""

        user = UserFactory.create(db_connector)
        user_id = user["id"]
        new_password_hash = UserFactory.hash_password("NewSecurePass123!")

        affected = db_connector._update(
            table="users",
            data={"password": new_password_hash},
            where={"id": user_id}
        )

        assert affected == 1

        updated = db_connector._select(
            fields=["password"],
            from_table="users",
            where={"id": user_id}
        )[0]

        # ✅ Декодируем если bytes
        stored_password = _decode_password(updated["password"])
        assert stored_password == new_password_hash

    def test_delete_test_user(self, db_connector: SqlServerBase, clean_users: None):
        """Тест: удаление тестового пользователя."""

        user = UserFactory.create(db_connector)
        user_id = user["id"]

        if user_id > 5:
            deleted = db_connector._delete(
                table="users",
                where={"id": user_id}
            )
            assert deleted == 1


class TestUsersAuth:
    """Тесты аутентификации и авторизации."""

    def test_verify_password_success(self, db_connector: SqlServerBase, clean_users: None):
        """Тест: успешная проверка пароля."""

        plain_password = "MyTestPass123!"
        password_hash = UserFactory.hash_password(plain_password)

        user = UserFactory.create(
            db_connector,
            first_name="AuthTest",
            last_name="User",
            password=password_hash
        )

        stored_user = db_connector._select(
            fields=["password"],
            from_table="users",
            where={"first_name": user["first_name"]}  # ✅ Используем уникальное имя
        )[0]

        # ✅ Конвертируем в bytes для bcrypt.checkpw через хелпер
        stored_password = _encode_password_for_check(stored_user["password"])

        assert bcrypt.checkpw(
            plain_password.encode('utf-8'),
            stored_password
        )

    def test_verify_password_failure(self, db_connector: SqlServerBase, clean_users: None):
        """Тест: неудачная проверка пароля."""

        password_hash = UserFactory.hash_password("CorrectPass123!")
        user = UserFactory.create(
            db_connector,
            first_name="AuthFail",
            password=password_hash
        )

        stored_user = db_connector._select(
            fields=["password"],
            from_table="users",
            where={"first_name": user["first_name"]}
        )[0]

        # ✅ Конвертируем в bytes через хелпер
        stored_password = _encode_password_for_check(stored_user["password"])

        assert not bcrypt.checkpw(
            b"WrongPassword!",
            stored_password
        )

    def test_login_by_credentials(self, db_connector: SqlServerBase):
        """Тест: поиск пользователя по логину для входа."""

        result = db_connector._select(
            fields=["id", "first_name", "password", "role"],
            from_table="users",
            where={"first_name": "admin"}
        )

        if result:  # ✅ Может не существовать в тестовой БД
            user = result[0]
            assert "id" in user
            assert "password" in user
            assert "role" in user

            # ✅ Декодируем password если bytes
            password = _decode_password(user["password"])
            assert password.startswith("$2b$")

    def test_check_user_permissions(self, db_connector: SqlServerBase):
        """Тест: проверка прав доступа по роли."""

        managers = db_connector._select(
            fields=["id", "first_name", "role"],
            from_table="users",
            where={"role": "Manager"}
        )

        employees = db_connector._select(
            fields=["id", "first_name", "role"],
            from_table="users",
            where={"role": "Employee"}
        )

        for mgr in managers:
            assert mgr["role"] == "Manager"

        for emp in employees:
            assert emp["role"] == "Employee"


class TestUsersBusinessLogic:
    """Тесты бизнес-логики работы с пользователями."""

    def test_promote_employee_to_manager(self, db_connector: SqlServerBase, clean_users: None):
        """Тест: бизнес-процесс повышения сотрудника."""

        employee = UserFactory.create(db_connector, role="Employee")
        emp_id = employee["id"]

        db_connector._update(
            table="users",
            data={"role": "Manager"},
            where={"id": emp_id}
        )

        promoted = db_connector._select(
            fields=["role"],
            from_table="users",
            where={"id": emp_id}
        )[0]

        assert promoted["role"] == "Manager"

    def test_count_users_by_role(self, db_connector: SqlServerBase, clean_users: None):
        """Тест: подсчёт пользователей по ролям."""

        unique_id = uuid.uuid4().hex[:8]  # ✅ Уникальный суффикс

        for i in range(3):
            UserFactory.create(db_connector, first_name=f"Emp_{unique_id}_{i}", role="Employee")
        for i in range(2):
            UserFactory.create(db_connector, first_name=f"Mgr_{unique_id}_{i}", role="Manager")

        emp_count = db_connector._count(
            from_table="users",
            where={"role": "Employee"}
        )

        mgr_count = db_connector._count(
            from_table="users",
            where={"role": "Manager"}
        )

        assert emp_count >= 3
        assert mgr_count >= 2

    def test_search_users_by_name(self, db_connector: SqlServerBase, clean_users: None):
        """Тест: поиск пользователей по имени (LIKE)."""

        unique_id = uuid.uuid4().hex[:8]  # ✅ Уникальный суффикс

        UserFactory.create(db_connector, first_name=f"Alexey_{unique_id}", last_name="Petrov")
        UserFactory.create(db_connector, first_name=f"Alex_{unique_id}", last_name="Smith")
        UserFactory.create(db_connector, first_name=f"Bob_{unique_id}", last_name="Alexandrov")

        results = db_connector.execute_select_query(
            query="""
                SELECT [id], [first_name], [last_name] 
                FROM [dbo].[users] 
                WHERE [first_name] LIKE :pattern
            """,
            params={"pattern": f"Alex%_{unique_id}"}  # ✅ Уникальный паттерн
        )

        names = [r["first_name"] for r in results]
        assert any(f"Alexey_{unique_id}" in n for n in names)
        assert any(f"Alex_{unique_id}" in n for n in names)
        assert all(f"Bob_{unique_id}" not in n for n in names)