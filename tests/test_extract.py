from unittest.mock import MagicMock
from extract import extract_table


def test_extract_table_truncates_and_loads_rows(pg_conn):
    # Seed a known row directly so we can verify TRUNCATE clears it
    with pg_conn.cursor() as cur:
        cur.execute(
            "INSERT INTO stg_products (product_id, created_at, product_name, description) "
            "VALUES (999, '2020-01-01', 'Old Row', '') "
            "ON CONFLICT (product_id) DO NOTHING"
        )
    pg_conn.commit()

    # Mock MySQL cursor returning one product row
    mysql_cur = MagicMock()
    mysql_cur.fetchall.return_value = [
        {
            "product_id": 99,
            "created_at": "2024-01-01 00:00:00",
            "product_name": "Test Basket",
            "description": "A test basket",
        }
    ]

    columns = ["product_id", "created_at", "product_name", "description"]

    with pg_conn.cursor() as pg_cur:
        count = extract_table(mysql_cur, pg_cur, "products", columns)
    pg_conn.commit()

    with pg_conn.cursor() as cur:
        cur.execute("SELECT product_id, product_name FROM stg_products ORDER BY product_id")
        rows = cur.fetchall()

    assert count == 1
    assert rows == [(99, "Test Basket")]   # old row (999) was truncated
