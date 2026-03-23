# tests/test_products.py
from decimal import Decimal
from Stock_Management_System.db.sqlserver_base import SqlServerBase
from Stock_Management_System.tests.db.factories.product_factory import ProductFactory


class TestProductsCRUD:
    """Тесты базовых операций с продуктами."""

    def test_insert_product(self, db_connector: SqlServerBase, clean_products: None):
        """Тест: вставка нового продукта."""

        product = ProductFactory.create(
            db_connector,
            name="Test Product",
            price=299.99,
            quantity=100,
            minimum_quantity=20
        )

        assert product is not None
        assert "id" in product
        assert product["name"] == "Test Product"
        assert float(product["price"]) == 299.99
        assert product["quantity"] == 100
        assert product["minimum_quantity"] == 20

    def test_select_product_by_id(self, db_connector: SqlServerBase, clean_products: None):
        """Тест: получение продукта по ID."""

        # Создаём продукт
        product = ProductFactory.create(db_connector, name="Find Me")
        product_id = product["id"]

        # Ищем по ID
        result = db_connector._select(
            fields=["id", "name", "price", "quantity"],
            from_table="products",
            where={"id": product_id}
        )

        assert len(result) == 1
        assert result[0]["name"] == "Find Me"
        assert float(result[0]["price"]) == 199.99

    def test_select_products_by_price_range(self, db_connector: SqlServerBase, clean_products: None):
        """Тест: выборка продуктов по диапазону цен."""

        # Создаём тестовые данные
        ProductFactory.create(db_connector, name="Cheap", price=10.00, quantity=100)
        ProductFactory.create(db_connector, name="Medium", price=150.00, quantity=50)
        ProductFactory.create(db_connector, name="Expensive", price=500.00, quantity=10)

        # Выборка: цена от 100 до 300
        results = db_connector.execute_select_query(
            query="""
                SELECT [name], [price] FROM [dbo].[products] 
                WHERE [price] BETWEEN :min_price AND :max_price
            """,
            params={"min_price": 100.0, "max_price": 300.0}
        )

        names = [r["name"] for r in results]
        assert "Medium" in names
        assert "Cheap" not in names
        assert "Expensive" not in names

    def test_update_product_quantity(self, db_connector: SqlServerBase, clean_products: None):
        """Тест: обновление количества товара."""

        product = ProductFactory.create(db_connector, quantity=50)
        product_id = product["id"]

        # Обновляем количество
        affected = db_connector._update(
            table="products",
            data={"quantity": 25},
            where={"id": product_id}
        )

        assert affected == 1

        # Проверяем обновление
        updated = db_connector._select(
            fields=["quantity"],
            from_table="products",
            where={"id": product_id}
        )[0]

        assert updated["quantity"] == 25

    def test_update_product_price(self, db_connector: SqlServerBase, clean_products: None):
        """Тест: обновление цены товара."""

        product = ProductFactory.create(db_connector, price=199.99)
        product_id = product["id"]

        # Обновляем цену
        affected = db_connector._update(
            table="products",
            data={"price": 149.99},
            where={"id": product_id}
        )

        assert affected == 1

        # Проверяем
        updated = db_connector._select(
            fields=["price"],
            from_table="products",
            where={"id": product_id}
        )[0]

        assert float(updated["price"]) == 149.99

    def test_delete_product(self, db_connector: SqlServerBase, clean_products: None):
        """Тест: удаление продукта."""

        product = ProductFactory.create(db_connector)
        product_id = product["id"]

        # Удаляем
        deleted = db_connector._delete(
            table="products",
            where={"id": product_id}
        )

        assert deleted == 1

        # Проверяем удаление
        result = db_connector._select(
            fields=["id"],
            from_table="products",
            where={"id": product_id}
        )

        assert len(result) == 0

    def test_select_low_stock_products(self, db_connector: SqlServerBase, clean_products: None):
        """Тест: выборка товаров с количеством ниже минимального."""

        # Создаём товары с разным запасом
        ProductFactory.create(db_connector, name="In Stock", quantity=100, minimum_quantity=10)
        ProductFactory.create(db_connector, name="Low Stock", quantity=5, minimum_quantity=10)
        ProductFactory.create(db_connector, name="Critical", quantity=2, minimum_quantity=20)

        # Выборка: quantity < minimum_quantity
        # Используем прямой запрос, т.к. _select не поддерживает операторы сравнения между колонками
        results = db_connector.execute_select_query(
            query="""
                SELECT [name], [quantity], [minimum_quantity] 
                FROM [dbo].[products] 
                WHERE [quantity] < [minimum_quantity]
                ORDER BY [quantity] ASC
            """
        )

        names = [r["name"] for r in results]
        assert "Low Stock" in names
        assert "Critical" in names
        assert "In Stock" not in names


class TestProductsBusinessLogic:
    """Тесты бизнес-логики работы с продуктами."""

    def test_decrease_quantity_on_sale(self, db_connector: SqlServerBase, clean_products: None):
        """Тест: уменьшение количества при продаже."""

        product = ProductFactory.create(db_connector, quantity=50, minimum_quantity=10)
        product_id = product["id"]
        sale_quantity = 15

        # Симуляция продажи: уменьшаем количество
        db_connector._update(
            table="products",
            data={"quantity": product["quantity"] - sale_quantity},
            where={"id": product_id}
        )

        # Проверяем новое количество
        updated = db_connector._select(
            fields=["quantity"],
            from_table="products",
            where={"id": product_id}
        )[0]

        assert updated["quantity"] == 35

    def test_check_stock_availability(self, db_connector: SqlServerBase, clean_products: None):
        """Тест: проверка доступности товара для заказа."""

        product = ProductFactory.create(db_connector, quantity=30, minimum_quantity=10)

        # Запрос на 25 штук — должен быть доступен
        available = db_connector.execute_select_query(
            query="""
                SELECT [id], [name] FROM [dbo].[products] 
                WHERE [id] = :id AND [quantity] >= :qty
            """,
            params={"id": product["id"], "qty": 25}
        )
        assert len(available) == 1

        # Запрос на 35 штук — не доступен
        not_available = db_connector._select(
            fields=["id"],
            from_table="products",
            where={"id": product["id"], "quantity": (35, 999999)}
        )
        assert len(not_available) == 0

    def test_bulk_insert_products(self, db_connector: SqlServerBase, clean_products: None):
        """Тест: массовая вставка продуктов через транзакцию."""

        import uuid
        unique_id = uuid.uuid4().hex[:8]

        products = [
            {"name": f"Bulk_{unique_id}_{i}", "price": 99.0 + i,
             "quantity": 50, "minimum_quantity": 10}
            for i in range(5)
        ]

        queries = [
            (
                """INSERT INTO [dbo].[products] ([name], [price], [quantity], [minimum_quantity]) 
                   VALUES (:name, :price, :quantity, :minimum_quantity)""",
                p
            )
            for p in products
        ]

        success = db_connector.execute_transaction(queries)
        assert success is True

        # Проверяем, что все вставлены
        count = db_connector._count(
            from_table="products",
            where={"name": tuple(f"Bulk_{unique_id}_{i}" for i in range(5))}
        )
        assert count == 5