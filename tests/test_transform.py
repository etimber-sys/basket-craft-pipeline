from decimal import Decimal
from datetime import date
from transform import transform


def test_transform_aggregates_by_product_and_month(pg_conn):
    with pg_conn.cursor() as cur:
        cur.execute("TRUNCATE stg_order_items, stg_products, monthly_sales")

        cur.execute("""
            INSERT INTO stg_products (product_id, created_at, product_name, description)
            VALUES
              (1, '2024-01-01', 'The Original Gift Basket', ''),
              (2, '2024-01-01', 'The Valentine''s Gift Basket', '')
        """)

        # Jan: product 1 ordered twice, product 2 ordered once
        # Feb: product 1 ordered once
        cur.execute("""
            INSERT INTO stg_order_items
              (order_item_id, created_at, order_id, product_id,
               is_primary_item, price_usd, cogs_usd)
            VALUES
              (1, '2024-01-10', 1, 1, 1, 50.00, 20.00),
              (2, '2024-01-20', 2, 1, 1, 50.00, 20.00),
              (3, '2024-01-25', 3, 2, 1, 75.00, 30.00),
              (4, '2024-02-05', 4, 1, 1, 50.00, 20.00)
        """)
    pg_conn.commit()

    transform(pg_conn)

    with pg_conn.cursor() as cur:
        cur.execute("""
            SELECT sale_month, product_id, order_count, revenue_usd, avg_order_value
            FROM monthly_sales
            ORDER BY sale_month, product_id
        """)
        rows = cur.fetchall()

    assert rows == [
        (date(2024, 1, 1), 1, 2, Decimal("100.00"), Decimal("50.00")),
        (date(2024, 1, 1), 2, 1, Decimal("75.00"),  Decimal("75.00")),
        (date(2024, 2, 1), 1, 1, Decimal("50.00"),  Decimal("50.00")),
    ]
