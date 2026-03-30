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
    """Load one MySQL table into its PostgreSQL staging counterpart.

    Args:
        mysql_cur: A pymysql DictCursor already connected to the source DB.
        pg_cur: A psycopg2 cursor already connected to the destination DB.
        table: Table name from the TABLES constant — must be a trusted,
               developer-controlled string, never user-supplied input.
        columns: Column list from the TABLES constant — same constraint.

    Returns:
        Number of rows loaded.

    Note: fetchall() materialises the full source table in memory before
    inserting. Acceptable for this project's scale; for large tables
    consider switching to SSCursor + fetchmany().
    """
    assert table in TABLES, f"Unknown table '{table}' — table must be a key in TABLES"
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
    """Extract all tables defined in TABLES from MySQL into PostgreSQL staging.

    Opens its own connections, performs a full TRUNCATE+INSERT for each table,
    commits, and closes connections. The MySQL cursor is a DictCursor (rows as
    dicts) as configured in get_mysql_conn().

    If an error occurs mid-extract, the PostgreSQL transaction is rolled back so
    staging tables are not left empty.
    """
    mysql_conn = get_mysql_conn()
    pg_conn = get_pg_conn()
    try:
        with mysql_conn.cursor() as mysql_cur, pg_conn.cursor() as pg_cur:  # mysql_cur is DictCursor (rows as dicts)
            for table, columns in TABLES.items():
                count = extract_table(mysql_cur, pg_cur, table, columns)
                print(f"  stg_{table}: {count} rows loaded")
        pg_conn.commit()
    except Exception:
        pg_conn.rollback()
        raise
    finally:
        mysql_conn.close()
        pg_conn.close()
