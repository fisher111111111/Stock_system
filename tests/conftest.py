# test/conftest.py
import os
import pytest
from playwright.sync_api import sync_playwright
from dotenv import load_dotenv
import pyodbc
import sqlalchemy
import bcrypt

load_dotenv(encoding='utf-8')

BASE_URL = "http://127.0.0.1:5000"

@pytest.fixture(scope="session")
def browser():
    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=False,  # True для CI/CD
            slow_mo=50       # Замедление для отладки
        )
        yield browser
        browser.close()

@pytest.fixture(scope="function")
def page(browser):
    context = browser.new_context(
        viewport=None,
        ignore_https_errors=True,
        base_url=BASE_URL
    )
    page = context.new_page()
    yield page
    context.close()


# --- Конфигурация подключения ---
DB_CONFIG = {
    'DRIVER': 'ODBC Driver 17 for SQL Server',
    'SERVER': 'localhost\\SQLEXPRESS', # или 'WIN-VIK827QHRC6\\SQLEXPRESS'
    'DATABASE': 'stock_db',
    'UID' : 'user',
    'PWD' : 'password1',
    'Timeout': 5,  # Таймаут подключения в секундах
}
#
# DRIVER_NAME = 'ODBC Driver 17 for SQL Server'
# SERVER_NAME = 'localhost\\SQLEXPRESS'   # или 'WIN-VIK827QHRC6\\SQLEXPRESS'
# DATABASE_NAME = 'stock_db'
# DB_USER = 'user'
# DB_PASSWORD = 'password1'

# ...
def check_db_connection():
    """Проверяет подключение к БД. Возвращает (True, None) или (False, ошибка)."""
    conn_str = (
        f"DRIVER={DB_CONFIG['DRIVER']};"
        f"SERVER={DB_CONFIG['SERVER']};"
        f"DATABASE={DB_CONFIG['DATABASE']};"
        f"UID={DB_CONFIG['UID']};"
        f"PWD={DB_CONFIG['PWD']};"
    )
    try:
        conn = pyodbc.connect(conn_str, timeout=DB_CONFIG['Timeout'])
        conn.close()
        return True, None
    except Exception as e:
        return False, str(e)


# --- Хук: Проверка перед сбором тестов ---
def pytest_configure(config):
    """Вызывается Pytest сразу после инициализации, до сбора тестов."""
    is_connected, error = check_db_connection()

    if not is_connected:
        # Сохраняем ошибку в конфиге, чтобы использовать в хуке сбора
        config._db_connection_error = error
    else:
        config._db_connection_error = None


# --- Хук: Остановка сбора тестов при ошибке ---
def pytest_collection(session):
    """Вызывается во время сбора тестов. Если вернуть не None, сбор прекратится."""
    if hasattr(session.config, '_db_connection_error') and session.config._db_connection_error:
        error_msg = session.config._db_connection_error
        # Выводим красивое сообщение в консоль
        reporter = session.config.pluginmanager.get_plugin("terminalreporter")
        if reporter:
            reporter.write_line("\n❌ ОШИБКА ПОДКЛЮЧЕНИЯ К БАЗЕ ДАННЫХ ❌", red=True)
            reporter.write_line(f"Не удалось подключиться к MS SQL Server: {error_msg}", red=True)
            reporter.write_line("Запуск тестов остановлен.\n", red=True)

        # Возвращаем код ошибки, чтобы pytest понял, что что-то не так
        return 1

    return None


@pytest.fixture(scope="session", autouse=True)
def setup_test_users():
    conn_str = f"DRIVER={DB_CONFIG['DRIVER']};SERVER={DB_CONFIG['SERVER']};DATABASE={DB_CONFIG['DATABASE']};UID={DB_CONFIG['UID']};PWD={DB_CONFIG['PWD']};"
    conn = pyodbc.connect(conn_str)
    cursor = conn.cursor()

    def hash_password(password):
        return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

    # Admin: логин "admin", пароль "admin", роль Manager
    admin_hashed = hash_password("admin")
    cursor.execute("""
        IF EXISTS (SELECT 1 FROM users WHERE first_name = 'admin')
            UPDATE users SET last_name = 'admin', password = ?, role = 'Manager' WHERE first_name = 'admin'
        ELSE
            INSERT INTO users (first_name, last_name, password, role) VALUES ('admin', 'admin', ?, 'Manager')
    """, (admin_hashed, admin_hashed))

    # Employee: логин "Worker", пароль "work", роль Employee
    worker_hashed = hash_password("work")
    cursor.execute("""
        IF EXISTS (SELECT 1 FROM users WHERE first_name = 'Worker')
            UPDATE users SET last_name = '', password = ?, role = 'Employee' WHERE first_name = 'Worker'
        ELSE
            INSERT INTO users (first_name, last_name, password, role) VALUES ('Worker', '', ?, 'Employee')
    """, (worker_hashed, worker_hashed))

    conn.commit()
    conn.close()


#     # --- Опционально: Фикстура для дублирования проверки ---
#
#
# @pytest.fixture(scope="session", autouse=True)
# def require_db_connection():
#     """
#     Страховочная фикстура.
#     Если хук выше по какой-то причине не сработает, эта фикстура упадет первой.
#     """
#     is_connected, error = check_db_connection()
#     if not is_connected:
#         pytest.fail(f"Нет подключения к БД: {error}", pytrace=False)

# --- Конфигурация подключения ---