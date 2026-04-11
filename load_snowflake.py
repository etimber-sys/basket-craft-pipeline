import os
import pandas as pd
import snowflake.connector
from snowflake.connector.pandas_tools import write_pandas
from dotenv import load_dotenv

from db import get_pg_conn

load_dotenv()

# Maps RDS staging table → Snowflake target table name (stg_ prefix dropped)
TABLES = {
    "stg_orders": "orders",
    "stg_order_items": "order_items",
    "stg_products": "products",
}


def _require_env(key):
    value = os.environ.get(key)
    if value is None:
        raise EnvironmentError(
            f"Required environment variable '{key}' is not set. "
            "Is your .env file configured?"
        )
    return value


def get_snowflake_conn():
    """Return a new Snowflake connection. Caller must close."""
    return snowflake.connector.connect(
        account=_require_env("SNOWFLAKE_ACCOUNT"),
        user=_require_env("SNOWFLAKE_USER"),
        password=_require_env("SNOWFLAKE_PASSWORD"),
        warehouse=_require_env("SNOWFLAKE_WAREHOUSE"),
        database=_require_env("SNOWFLAKE_DATABASE"),
        schema=_require_env("SNOWFLAKE_SCHEMA"),
        role=_require_env("SNOWFLAKE_ROLE"),
        login_timeout=30,
        network_timeout=60,
    )


def load_table(pg_conn, sf_conn, source_table, target_table):
    """Read one RDS staging table and write it to Snowflake.

    Args:
        pg_conn: Open psycopg2 connection to RDS.
        sf_conn: Open Snowflake connection.
        source_table: Staging table name in RDS (e.g. 'stg_orders').
        target_table: Target table name in Snowflake (e.g. 'orders').

    Returns:
        Number of rows loaded.
    """
    with pg_conn.cursor() as cur:
        cur.execute(f"SELECT * FROM {source_table}")
        rows = cur.fetchall()
        col_names = [desc[0] for desc in cur.description]

    df = pd.DataFrame(rows, columns=col_names)

    success, _, nrows, _ = write_pandas(
        sf_conn,
        df,
        target_table.upper(),
        quote_identifiers=False,
        auto_create_table=True,
        overwrite=True,
    )

    if not success:
        raise RuntimeError(f"write_pandas failed for table '{target_table}'")

    return nrows


def load_snowflake():
    """Load all raw Basket Craft tables from RDS into Snowflake.

    Opens its own connections, TRUNCATEs each Snowflake target table,
    then bulk-loads rows via write_pandas. Closes connections when done.

    If an error occurs, the run halts immediately. Tables already completed
    remain loaded; the in-progress table is left empty after TRUNCATE.
    """
    print("Connecting to RDS...")
    pg_conn = get_pg_conn()
    print("Connected to RDS.")
    print("Connecting to Snowflake...")
    sf_conn = get_snowflake_conn()
    print("Connected to Snowflake.")
    try:
        for source_table, target_table in TABLES.items():
            print(f"Loading {target_table} into Snowflake...")
            count = load_table(pg_conn, sf_conn, source_table, target_table)
            print(f"  {target_table}: {count:,} rows loaded")
    finally:
        pg_conn.close()
        sf_conn.close()


if __name__ == "__main__":
    load_snowflake()
    print("Done.")
