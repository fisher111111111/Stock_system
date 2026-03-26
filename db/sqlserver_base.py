# db/sqlserver_base.py
import os
from typing import Optional, List, Dict, Any
from urllib.parse import quote_plus

from sqlalchemy import create_engine, text
from sqlalchemy.types import LargeBinary

from ..db.db_base import DbBase, DatabaseException


class SqlServerBase(DbBase):
    """SQL Server connector using SQLAlchemy + pyodbc."""

    def __init__(self, logger_name: Optional[str] = None):
        super().__init__(logger_name)
        self._connection_params: Dict[str, Any] = {}

    def connect(
            self,
            db_name: str,
            host: Optional[str] = None,
            port: Optional[int] = None,
            user: Optional[str] = None,
            password: Optional[str] = None,
            driver: Optional[str] = None,
            trusted_connection: bool = False,
            **kwargs
    ):
        """Establish connection to SQL Server database."""

        # Чтение настроек из env или использование дефолтов
        host = host or os.getenv("MSSQL_HOST", "localhost")
        port = port or int(os.getenv("MSSQL_PORT", "1433"))
        user = user or os.getenv("MSSQL_USER", "user")
        password = password or os.getenv("MSSQL_PASSWORD", "password1")
        driver = driver or os.getenv("MSSQL_DRIVER", "ODBC Driver 17 for SQL Server")

        self.logger.info(
            f"Connecting to SQL Server: {host}:{port}/{db_name} (user: {user})"
        )

        self.close()

        # Формирование connection string
        if trusted_connection:
            conn_str = (
                f"DRIVER={{{driver}}};"
                f"SERVER={host},{port};"
                f"DATABASE={db_name};"
                f"Trusted_Connection=yes;"
            )
        else:
            conn_str = (
                f"DRIVER={{{driver}}};"
                f"SERVER={host},{port};"
                f"DATABASE={db_name};"
                f"UID={user};"
                f"PWD={password};"
            )

        # Добавление дополнительных параметров
        for key, value in kwargs.items():
            conn_str += f"{key}={value};"

        # URL-encoding для специальных символов
        conn_str_encoded = quote_plus(conn_str)
        connection_url = f"mssql+pyodbc:///?odbc_connect={conn_str_encoded}"

        self.engine = create_engine(
            connection_url,
            pool_pre_ping=True,
            pool_recycle=3600,
            echo=os.getenv("DB_ECHO", "false").lower() == "true"
        )

        self.connection = self.engine.connect()
        self._db_name = db_name
        self._connection_params = {
            "db_name": db_name, "host": host, "port": port,
            "user": user, "password": password, "driver": driver,
            "trusted_connection": trusted_connection, **kwargs
        }
        self.logger.info("Connection established successfully")

    def _check_connection(self) -> None:
        """Check and restore connection if needed."""
        if self.connection is None or self.connection.closed:
            self.logger.warning("Connection lost, reconnecting...")
            if not self._connection_params:
                raise DatabaseException("Cannot reconnect: no connection parameters")
            self.connect(**self._connection_params)

    def execute_query(self, query: str, params: Optional[Dict] = None) -> int:
        self._check_connection()
        return super().execute_query(query, params)

    def execute_select_query(self, query: str, params: Optional[Dict] = None) -> List[Dict]:
        self._check_connection()
        return super().execute_select_query(query, params)

    def execute_transaction(self, queries: List[tuple]) -> bool:
        """
        Execute multiple queries in a single transaction.
        queries: list of tuples (query_string, params_dict)
        """
        self._check_connection()
        try:
            for query, params in queries:
                self.connection.execute(text(query), params or {})
            self.connection.commit()
            self.logger.info("Transaction completed successfully")
            return True
        except Exception as e:
            self.connection.rollback()
            self.logger.error(f"Transaction failed: {e}")
            raise

    # === Helper-методы для построения запросов ===

    def _select(
            self,
            fields: List[str],
            from_table: str,
            where: Optional[Dict[str, Any]] = None,
            order_by: Optional[str] = None,
            order_direction: str = "ASC",
            limit: Optional[int] = None,
            schema: str = "dbo",
    ) -> List[Dict[str, Any]]:
        """Build and execute SELECT query with parameters."""
        self._check_connection()

        query_parts = [f"SELECT {', '.join(fields)}", f"FROM [{schema}].[{from_table}]"]
        params = {}

        if where:
            conditions = []
            for idx, (key, value) in enumerate(where.items()):
                if isinstance(value, (list, tuple)):
                    placeholders = [f":p{i}_{key}" for i in range(len(value))]
                    conditions.append(f"{key} IN ({', '.join(placeholders)})")
                    for i, v in enumerate(value):
                        params[f"p{i}_{key}"] = v
                elif value is None:
                    conditions.append(f"{key} IS NULL")
                else:
                    param_name = f"p_{key}"
                    conditions.append(f"{key} = :{param_name}")
                    params[param_name] = value
            query_parts.append(f"WHERE {' AND '.join(conditions)}")

        if order_by:
            query_parts.append(f"ORDER BY {order_by} {order_direction.upper()}")

        if limit:
            query_parts.append(f"OFFSET 0 ROWS FETCH NEXT {limit} ROWS ONLY")

        query = " ".join(query_parts)
        return self.execute_select_query(query, params)

    def _count(
            self,
            from_table: str,
            where: Optional[Dict] = None,
            schema: str = "dbo",
    ) -> int:
        """Get count of records matching conditions."""
        result = self._select(
            fields=["COUNT(*) as cnt"],
            from_table=from_table,
            where=where,
            schema=schema
        )
        return result[0]["cnt"] if result else 0


    def _insert(self, table: str, data: dict, schema: str = "dbo") -> int:
        """Insert single record with automatic password conversion."""
        self._check_connection()
        if not data:
            raise ValueError("Cannot insert empty data")

        # ✅ Авто-конвертация password для VARBINARY колонки
        if table == "users" and "password" in data:
            if isinstance(data["password"], str):
                # ✅ Оборачиваем в Binary() для корректной передачи в VARBINARY
                data["password"] = LargeBinary(data["password"].encode('utf-8'))

        columns = ", ".join(f"[{k}]" for k in data.keys())
        placeholders = ", ".join(f":{k}" for k in data.keys())
        query = f"INSERT INTO [{schema}].[{table}] ({columns}) VALUES ({placeholders})"
        return self.execute_query(query, data)

    def _update(
            self,
            table: str,
            data: dict,
            where: Dict[str, Any],
            schema: str = "dbo"
    ) -> int:
        """Update records matching conditions."""
        self._check_connection()
        if not data:
            raise ValueError("Cannot update with empty data")
        if not where:
            raise ValueError("UPDATE requires WHERE clause for safety")

        set_clause = ", ".join(f"[{k}] = :{k}" for k in data.keys())
        conditions = []
        params = dict(data)

        for key, value in where.items():
            param_name = f"w_{key}"
            conditions.append(f"[{key}] = :{param_name}")
            params[param_name] = value

        query = f"UPDATE [{schema}].[{table}] SET {set_clause} WHERE {' AND '.join(conditions)}"
        return self.execute_query(query, params)

    def _delete(
            self,
            table: str,
            where: Dict[str, Any],
            schema: str = "dbo"
    ) -> int:
        """Delete records matching conditions."""
        self._check_connection()
        if not where:
            raise ValueError("DELETE requires WHERE clause for safety")

        conditions = []
        params = {}
        for key, value in where.items():
            param_name = f"w_{key}"
            conditions.append(f"[{key}] = :{param_name}")
            params[param_name] = value

        query = f"DELETE FROM [{schema}].[{table}] WHERE {' AND '.join(conditions)}"
        return self.execute_query(query, params)