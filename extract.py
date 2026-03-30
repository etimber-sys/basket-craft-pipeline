from db import get_mysql_conn, get_pg_conn

TABLES = {
    "orders": [
        "order_id", "created_at", "website_session_id", "user_id",
        "primary_product_id", "items_purchased", "price_usd", "cogs_usd",
    ],
    "order_items": [
        "order_item_id", "created_at", "order_id", "product_id",
        "is_primary_item", "price_usd", "cogs_usd",
    ],
    "products": [
        "product_id", "created_at", "product_name", "description",
    ],
}

BATCH_SIZE = 1000


def extract_table(mysql_cur, pg_cur, table, columns):
    col_list = ", ".join(columns)
    placeholders = ", ".join(["%s"] * len(columns))

    mysql_cur.execute(f"SELECT {col_list} FROM {table}")
    rows = mysql_cur.fetchall()

    pg_cur.execute(f"TRUNCATE stg_{table}")

    if rows:
        values = [tuple(row[col] for col in columns) for row in rows]
        for i in range(0, len(values), BATCH_SIZE):
            pg_cur.executemany(
                f"INSERT INTO stg_{table} ({col_list}) VALUES ({placeholders})",
                values[i : i + BATCH_SIZE],
            )

    return len(rows)


def extract():
    mysql_conn = get_mysql_conn()
    pg_conn = get_pg_conn()
    try:
        with mysql_conn.cursor() as mysql_cur, pg_conn.cursor() as pg_cur:
            for table, columns in TABLES.items():
                count = extract_table(mysql_cur, pg_cur, table, columns)
                print(f"  stg_{table}: {count} rows loaded")
        pg_conn.commit()
    finally:
        mysql_conn.close()
        pg_conn.close()
