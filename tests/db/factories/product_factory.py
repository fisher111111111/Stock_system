# tests/factories/product_factory.py
import uuid
from decimal import Decimal
from typing import Optional

from .... db.sqlserver_base import SqlServerBase


class ProductFactory:
    """Фабрика для создания тестовых данных продукта."""

    @staticmethod
    def build(
            name: Optional[str] = None,
            price: Optional[float] = None,
            quantity: Optional[int] = None,
            minimum_quantity: Optional[int] = None,
            **overrides
    ) -> dict:
        """Создать словарь данных продукта."""
        unique_suffix = uuid.uuid4().hex[:8]

        base = {
            "name": name or f"Product_{unique_suffix}",
            "price": Decimal(str(price)) if price is not None else Decimal("199.99"),
            "quantity": quantity if quantity is not None else 50,
            "minimum_quantity": minimum_quantity if minimum_quantity is not None else 10,
        }
        base.update(overrides)
        return base

    @staticmethod
    def create(db: SqlServerBase, **overrides) -> dict:
        """Создать и вставить продукт в БД, вернуть данные с ID."""
        data = ProductFactory.build(**overrides)
        db._insert(table="products", data=data)

        # Получаем вставленную запись с ID
        result = db._select(
            fields=["*"],
            from_table="products",
            where={"name": data["name"]}
        )
        return result[0] if result else None