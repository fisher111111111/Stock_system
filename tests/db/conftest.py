# tests/db/conftest.py
import os
import pytest
import logging
from datetime import datetime
from typing import Generator

from Stock_Management_System.db.sqlserver_base import SqlServerBase


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
    """Очистка таблицы users до/после теста."""
    # Не удаляем системных пользователей (id <= 5), если они нужны
    db_connector.execute_query("DELETE FROM [dbo].[users] WHERE [id] > 3")
    yield
    db_connector.execute_query("DELETE FROM [dbo].[users] WHERE [id] > 3")