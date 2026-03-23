# db/db_base.py
import logging
from abc import ABC
from datetime import datetime
from typing import List, Optional, Any, Dict
from uuid import UUID
from contextlib import contextmanager

from sqlalchemy import text, Engine
from sqlalchemy.engine import Connection
from sqlalchemy.exc import SQLAlchemyError


# Простое исключение для ошибок БД
class DatabaseException(Exception):
    """Base exception for database operations."""
    pass


class DbBase(ABC):
    """Базовый синхронный коннектор БД использующий SQLAlchemy."""

    def __init__(self, logger_name: Optional[str] = None):
        self.engine: Optional[Engine] = None
        self.connection: Optional[Connection] = None
        self._db_name: Optional[str] = None

        # Настройка логгера
        self.logger = logging.getLogger(logger_name or f"db.{self.__class__.__name__}")
        if not self.logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                '%(asctime)s [%(levelname)s] %(name)s: %(message)s',
                datefmt='%H:%M:%S'
            )
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)
            self.logger.setLevel(logging.INFO)

    def close(self):
        """Закрыть соединение и остановить движок"""
        if self.connection:
            self.logger.info("Closing database connection")
            self.connection.close()
            self.connection = None
        if self.engine:
            self.engine.dispose()
            self.engine = None

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
        return False

    @contextmanager
    def _query_context(self, operation: str, query: str):
        """Контекстный менеджер для логирования запросов."""
        self.logger.info(f"[{operation}] Executing: {query.strip()}")
        start = datetime.now()
        try:
            yield
            duration = (datetime.now() - start).total_seconds() * 1000
            self.logger.info(f"[{operation}] Completed in {duration:.1f}ms")
        except Exception as e:
            duration = (datetime.now() - start).total_seconds() * 1000
            self.logger.error(f"[{operation}] Failed after {duration:.1f}ms: {e}")
            raise

    def execute_select_query(
            self,
            query: str,
            params: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """ Выполнение запроса SELECT и возврат списка со словарями"""
        if not self.connection:
            raise DatabaseException("No active database connection")

        with self._query_context("SELECT", query):
            try:
                result = self.connection.execute(text(query), params or {})
                data = [dict(row) for row in result.mappings()]
                self.logger.debug(f"SELECT returned {len(data)} rows")
                return data
            except SQLAlchemyError as e:
                raise DatabaseException(f"Query execution failed: {e}")

    def execute_query(
            self,
            query: str,
            params: Optional[Dict[str, Any]] = None
    ) -> int:
        """ Выполнение запросов INSERT/UPDATE/DELETE, возвращает количество затронутых строк."""
        if not self.connection:
            raise DatabaseException("No active database connection")

        operation = query.strip().split()[0].upper()
        with self._query_context(operation, query):
            try:
                result = self.connection.execute(text(query), params or {})
                self.connection.commit()
                rowcount = result.rowcount
                self.logger.info(f"{operation} affected {rowcount} row(s)")
                return rowcount
            except SQLAlchemyError as e:
                self.connection.rollback()
                raise DatabaseException(f"Query execution failed: {e}")

    @staticmethod
    def check_uuids_list(list_ids: List[str]) -> None:
        """Проверка, что все элементы в списке являются допустимыми строками UUID."""
        if not isinstance(list_ids, list):
            raise ValueError(f"Expected list of strings, got {type(list_ids).__name__}")
        for item in list_ids:
            if not isinstance(item, str):
                raise ValueError(f"Expected string UUID, got {type(item).__name__}")
            UUID(item)  # Raises ValueError if invalid