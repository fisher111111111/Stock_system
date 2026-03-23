# tests/conftest.py
import pytest
import logging
import os
from datetime import datetime
from typing import Generator

from playwright.sync_api import sync_playwright, Page, Browser
from Stock_Management_System.db.sqlserver_base import SqlServerBase  # ✅ Исправлен импорт (убран лишний пробел)

# === Настройки ===
BASE_URL = os.getenv("BASE_URL", "http://127.0.0.1:5000")


# === Настройка логирования (ПРАВИЛЬНЫЙ ХУК) ===
# ✅ ИСПРАВЛЕНО: pytest_configure вместо pytest_logger
def pytest_configure(config):
    """Настройка логирования перед запуском тестов."""
    logging.basicConfig(
        level=getattr(logging, os.getenv("LOG_LEVEL", "INFO")),
        format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
        datefmt='%H:%M:%S',
        force=True  # Перезаписывает существующие хендлеры
    )


# === Проверка подключения к БД перед запуском ===
def check_db_connection() -> tuple[bool, str | None]:
    """Проверяет подключение к БД. Возвращает (True, None) или (False, ошибка)."""
    import pyodbc

    db_config = {
        'DRIVER': '{ODBC Driver 17 for SQL Server}',
        'SERVER': os.getenv("MSSQL_HOST", "localhost\\SQLEXPRESS"),
        'DATABASE': os.getenv("MSSQL_TEST_DB", "stock_db"),
        'UID': os.getenv("MSSQL_USER", "user"),
        'PWD': os.getenv("MSSQL_PASSWORD", "password1"),
        'Timeout': 5,
    }

    conn_str = (
        f"DRIVER={db_config['DRIVER']};"
        f"SERVER={db_config['SERVER']};"
        f"DATABASE={db_config['DATABASE']};"
        f"UID={db_config['UID']};"
        f"PWD={db_config['PWD']};"
    )

    try:
        conn = pyodbc.connect(conn_str, timeout=db_config['Timeout'])
        conn.close()
        return True, None
    except Exception as e:
        return False, str(e)


# === Хук: остановка при ошибке подключения к БД ===
# ✅ ИСПРАВЛЕНО: правильный возврат значения
def pytest_collection(session) -> None:
    """Вызывается во время сбора тестов."""
    is_connected, error = check_db_connection()

    if not is_connected:
        reporter = session.config.pluginmanager.get_plugin("terminalreporter")
        if reporter:
            reporter.write_line("\n❌ ОШИБКА ПОДКЛЮЧЕНИЯ К БАЗЕ ДАННЫХ ❌", bold=True, red=True)
            reporter.write_line(f"Не удалось подключиться к MS SQL Server: {error}", red=True)
            reporter.write_line("Запуск тестов остановлен.\n", red=True)
        # ✅ Правильный способ остановить тесты: выбросить исключение
        raise pytest.UsageError(f"Database connection failed: {error}")


# === Фикстура: имя тестовой БД ===
# ✅ ДОБАВЛЕНО: отсутствующая фикстура
# @pytest.fixture(scope="session")
# def test_db_name() -> str:
#     """Уникальное имя тестовой БД для изоляции."""
#     return os.getenv("MSSQL_TEST_DB", "stock_db")


# === Фикстуры Playwright ===
@pytest.fixture(scope="session")
def browser() -> Generator[Browser, None, None]:
    """Браузер для всех тестов в сессии."""
    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=os.getenv("CI") == "true",  # Headless в CI
            slow_mo=50 if os.getenv("DEBUG") else 0  # Замедление при отладке
        )
        yield browser
        browser.close()


@pytest.fixture(scope="function")
def page(browser: Browser) -> Generator[Page, None, None]:
    """Новая страница для каждого теста."""
    context = browser.new_context(
        viewport={"width": 1920, "height": 1080},
        ignore_https_errors=True,
        base_url=BASE_URL
    )
    page = context.new_page()
    yield page
    context.close()


# === Фикстуры для БД ===
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
    """Очистка таблицы products до/после теста (только тестовые данные)."""
    # Удаляем только тестовые записи (id > 100)
    db_connector.execute_query("DELETE FROM [dbo].[products] WHERE [id] > 100")
    yield
    db_connector.execute_query("DELETE FROM [dbo].[products] WHERE [id] > 100")


@pytest.fixture(scope="function")
def clean_users(db_connector: SqlServerBase) -> Generator[None, None, None]:
    """Очистка таблицы users до/после теста (сохраняем системных пользователей)."""
    # Сохраняем пользователей с id <= 5 (admin, alex, etc.)
    db_connector.execute_query("DELETE FROM [dbo].[users] WHERE [id] > 5")
    yield
    db_connector.execute_query("DELETE FROM [dbo].[users] WHERE [id] > 5")