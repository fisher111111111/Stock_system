# db/async_sqlserver_base.py
import os
import asyncio
import logging
from typing import Optional, List, Dict, Any
from contextlib import asynccontextmanager

import aioodbc

from Stock_Management_System.db.db_base import DatabaseException


class AsyncSqlServerBase:
    """Async SQL Server connector using aioodbc."""

    def __init__(self, logger_name: Optional[str] = None):
        self.connection = None
        self._connection_params: Dict[str, Any] = {}
        self._db_name: Optional[str] = None

        self.logger = logging.getLogger(logger_name or "db.AsyncSqlServerBase")
        if not self.logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                '%(asctime)s [%(levelname)s] %(name)s: %(message)s',
                datefmt='%H:%M:%S'
            )
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)
            self.logger.setLevel(logging.INFO)

    async def close(self):
        """Close async connection."""
        if self.connection:
            self.logger.info("Closing async database connection")
            await self.connection.close()
            self.connection = None

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()
        return False

    @asynccontextmanager
    async def _query_context(self, operation: str, query: str):
        """Async context manager for query logging."""
        self.logger.info(f"[{operation}] Executing: {query.strip()}")
        start = asyncio.get_event_loop().time()
        try:
            yield
            duration = (asyncio.get_event_loop().time() - start) * 1000
            self.logger.info(f"[{operation}] Completed in {duration:.1f}ms")
        except Exception as e:
            duration = (asyncio.get_event_loop().time() - start) * 1000
            self.logger.error(f"[{operation}] Failed after {duration:.1f}ms: {e}")
            raise

    async def connect(
            self,
            db_name: str,
            host: Optional[str] = None,
            port: Optional[int] = None,
            user: Optional[str] = None,
            password: Optional[str] = None,
            driver: Optional[str] = None,
            timeout: int = 30,
            **kwargs
    ):
        """Establish async connection to SQL Server."""
        host = host or os.getenv("MSSQL_HOST", "localhost")
        port = port or int(os.getenv("MSSQL_PORT", "1433"))
        user = user or os.getenv("MSSQL_USER", "sa")
        password = password or os.getenv("MSSQL_PASSWORD", "")
        driver = driver or os.getenv("MSSQL_DRIVER", "ODBC Driver 17 for SQL Server")

        self.logger.info(
            f"Connecting async to SQL Server: {host}:{port}/{db_name}"
        )

        await self.close()

        conn_str = (
            f"DRIVER={{{driver}}};"
            f"SERVER={host},{port};"
            f"DATABASE={db_name};"
            f"UID={user};"
            f"PWD={password};"
            f"Timeout={timeout};"
            f"Encrypt=yes;"
            f"TrustServerCertificate=yes;"
        )

        for key, value in kwargs.items():
            conn_str += f"{key}={value};"

        self.connection = await aioodbc.connect(
            dsn=conn_str,
            autocommit=False
        )
        self._db_name = db_name
        self._connection_params = {
            "db_name": db_name, "host": host, "port": port,
            "user": user, "password": password, "driver": driver,
            "timeout": timeout, **kwargs
        }
        self.logger.info("Async connection established")

    async def _check_connection(self) -> None:
        """Reconnect if connection is closed."""
        if self.connection is None or self.connection.closed:
            self.logger.warning("Async connection lost, reconnecting...")
            if not self._connection_params:
                raise DatabaseException("Cannot reconnect: no connection parameters")
            await self.connect(**self._connection_params)

    async def execute_select_query(
            self,
            query: str,
            params: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """Execute SELECT query asynchronously."""
        await self._check_connection()

        async with self._query_context("SELECT", query):
            try:
                cursor = await self.connection.cursor()
                await cursor.execute(query, params or {})

                if cursor.description:
                    columns = [col[0] for col in cursor.description]
                    rows = await cursor.fetchall()
                    result = [dict(zip(columns, row)) for row in rows]
                else:
                    result = []

                await cursor.close()
                self.logger.debug(f"Async SELECT returned {len(result)} rows")
                return result
            except Exception as e:
                raise DatabaseException(f"Async query failed: {e}")

    async def execute_query(
            self,
            query: str,
            params: Optional[Dict[str, Any]] = None
    ) -> int:
        """Execute write query asynchronously."""
        await self._check_connection()

        operation = query.strip().split()[0].upper()
        async with self._query_context(operation, query):
            try:
                cursor = await self.connection.cursor()
                await cursor.execute(query, params or {})
                rowcount = cursor.rowcount
                await self.connection.commit()
                await cursor.close()
                self.logger.info(f"Async {operation} affected {rowcount} row(s)")
                return rowcount
            except Exception as e:
                await self.connection.rollback()
                raise DatabaseException(f"Async write query failed: {e}")

    async def execute_transaction(
            self,
            queries: List[tuple]
    ) -> bool:
        """Execute multiple queries in single async transaction."""
        await self._check_connection()
        try:
            cursor = await self.connection.cursor()
            for query, params in queries:
                await cursor.execute(query, params or {})
            await self.connection.commit()
            await cursor.close()
            self.logger.info("Async transaction completed")
            return True
        except Exception as e:
            await self.connection.rollback()
            self.logger.error(f"Async transaction failed: {e}")
            raise

    # === Helper methods ===

    async def _select(
            self,
            fields: List[str],
            from_table: str,
            where: Optional[Dict[str, Any]] = None,
            order_by: Optional[str] = None,
            order_direction: str = "ASC",
            limit: Optional[int] = None,
            schema: str = "dbo",
    ) -> List[Dict[str, Any]]:
        """Build and execute async SELECT."""
        await self._check_connection()

        query_parts = [f"SELECT {', '.join(fields)}", f"FROM [{schema}].[{from_table}]"]
        params = {}

        if where:
            conditions = []
            for key, value in where.items():
                if isinstance(value, (list, tuple)):
                    placeholders = [f"@p{i}_{key}" for i in range(len(value))]
                    conditions.append(f"{key} IN ({', '.join(placeholders)})")
                    for i, v in enumerate(value):
                        params[f"p{i}_{key}"] = v
                elif value is None:
                    conditions.append(f"{key} IS NULL")
                else:
                    param_name = f"p_{key}"
                    conditions.append(f"{key} = @{param_name}")
                    params[param_name] = value
            query_parts.append(f"WHERE {' AND '.join(conditions)}")

        if order_by:
            query_parts.append(f"ORDER BY {order_by} {order_direction.upper()}")

        if limit:
            query_parts.append(f"OFFSET 0 ROWS FETCH NEXT {limit} ROWS ONLY")

        query = " ".join(query_parts)
        return await self.execute_select_query(query, params)

    async def _count(
            self,
            from_table: str,
            where: Optional[Dict] = None,
            schema: str = "dbo",
    ) -> int:
        """Get async count of records."""
        result = await self._select(
            fields=["COUNT(*) as cnt"],
            from_table=from_table,
            where=where,
            schema=schema
        )
        return result[0]["cnt"] if result else 0

    async def _insert(self, table: str, data: dict, schema: str = "dbo") -> int:
        """Async INSERT single record."""
        await self._check_connection()
        if not data:
            raise ValueError("Cannot insert empty data")

        columns = ", ".join(f"[{k}]" for k in data.keys())
        placeholders = ", ".join(f"@{k}" for k in data.keys())
        query = f"INSERT INTO [{schema}].[{table}] ({columns}) VALUES ({placeholders})"
        return await self.execute_query(query, data)

    async def _update(
            self,
            table: str,
            data: dict,
            where: Dict[str, Any],
            schema: str = "dbo"
    ) -> int:
        """Async UPDATE records."""
        await self._check_connection()
        if not data:
            raise ValueError("Cannot update with empty data")
        if not where:
            raise ValueError("UPDATE requires WHERE clause")

        set_clause = ", ".join(f"[{k}] = @{k}" for k in data.keys())
        conditions = []
        params = dict(data)

        for key, value in where.items():
            param_name = f"w_{key}"
            conditions.append(f"[{key}] = @{param_name}")
            params[param_name] = value

        query = f"UPDATE [{schema}].[{table}] SET {set_clause} WHERE {' AND '.join(conditions)}"
        return await self.execute_query(query, params)

    async def _delete(
            self,
            table: str,
            where: Dict[str, Any],
            schema: str = "dbo"
    ) -> int:
        """Async DELETE records."""
        await self._check_connection()
        if not where:
            raise ValueError("DELETE requires WHERE clause")

        conditions = []
        params = {}
        for key, value in where.items():
            param_name = f"w_{key}"
            conditions.append(f"[{key}] = @{param_name}")
            params[param_name] = value

        query = f"DELETE FROM [{schema}].[{table}] WHERE {' AND '.join(conditions)}"
        return await self.execute_query(query, params)
