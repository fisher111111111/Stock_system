# tests/db/conftest.py
# import os
# import sys
#
# import pytest
# import logging
# from datetime import datetime
# from typing import Generator
# import bcrypt
#
# # from Stock_Management_System.db.sqlserver_base import SqlServerBase
# # Добавляем корень проекта в sys.path
# sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))
#
# # Теперь можно импортировать из пакета db
# # from Stock_Management_System.db.sqlserver_base import SqlServerBase
# from db.sqlserver_base import SqlServerBase

import os
import sys
import pytest
import logging
from datetime import datetime
from typing import Generator
import bcrypt

# Добавляем корень проекта в sys.path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '../..'))
print(f"DEBUG: project_root = {project_root}")
print(f"DEBUG: sys.path before = {sys.path}")
sys.path.insert(0, project_root)
print(f"DEBUG: sys.path after = {sys.path}")

# Проверяем содержимое папки db
db_path = os.path.join(project_root, 'db')
if os.path.exists(db_path):
    print(f"DEBUG: Contents of {db_path}: {os.listdir(db_path)}")
else:
    print(f"DEBUG: {db_path} does not exist!")

# Импортируем
try:
    from db.sqlserver_base import SqlServerBase
    print("DEBUG: Import successful")
except ImportError as e:
    print(f"DEBUG: Import error: {e}")
    raise

def pytest_configure(config):
    """Настройка логирования для тестов."""
    logging.basicConfig(
        level=getattr(logging, os.getenv("LOG_LEVEL", "INFO")),
        format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
        datefmt='%H:%M:%S'
    )


@pytest.fixture(scope="session")
def test_db_name() -> str:
    """Уникальное имя тестовой БД."""
    return os.getenv("MSSQL_TEST_DB", 'stock_db')


@pytest.fixture(scope="function")
def db_connector(test_db_name: str) -> Generator[SqlServerBase, None, None]:
    """Подключение к БД для каждого теста."""
    db = SqlServerBase(logger_name=f"test.{datetime.now().strftime('%H%M%S')}")
    try:
        db.connect(db_name=test_db_name)
        yield db
    finally:
        db.close()


@pytest.fixture(scope="function")
def db_transaction(db_connector: SqlServerBase) -> Generator[SqlServerBase, None, None]:
    """Тест в транзакции с автоматическим откатом."""
    db_connector.connection.begin()
    try:
        yield db_connector
        db_connector.connection.rollback()
    except Exception:
        db_connector.connection.rollback()
        raise

@pytest.fixture(scope="function")
def clean_products(db_connector: SqlServerBase) -> Generator[None, None, None]:
    """Очистка таблицы products до/после теста."""
    db_connector.execute_query("DELETE FROM [dbo].[products]")
    yield
    db_connector.execute_query("DELETE FROM [dbo].[products]")

@pytest.fixture(scope="function")
def clean_users(db_connector: SqlServerBase) -> Generator[None, None, None]:
    """Очистка таблицы users до/после теста. Сохраняются первые 3 пользователя."""
    db_connector.execute_query("""
        DELETE FROM [dbo].[users] 
        WHERE [id] NOT IN (
            SELECT TOP 3 [id] 
            FROM [dbo].[users] 
            ORDER BY [id] ASC
        )
    """)
    yield
    db_connector.execute_query("""
        DELETE FROM [dbo].[users] 
        WHERE [id] NOT IN (
            SELECT TOP 3 [id] 
            FROM [dbo].[users] 
            ORDER BY [id] ASC
        )
    """)
