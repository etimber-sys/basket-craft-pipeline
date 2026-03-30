# Basket Craft ELT Pipeline Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build an ELT pipeline that extracts orders/products from MySQL, loads them into PostgreSQL staging tables, and aggregates into a `monthly_sales` fact table.

**Architecture:** Python script (`pipeline.py`) orchestrates two phases: `extract()` copies three MySQL tables into PostgreSQL staging tables via full TRUNCATE+INSERT; `transform()` runs a single SQL aggregation inside PostgreSQL to produce `monthly_sales`. All transformation logic stays in SQL.

**Tech Stack:** Python 3, pymysql, psycopg2-binary, python-dotenv, pytest, PostgreSQL 16 (Docker)

---

## File Map

| File | Responsibility |
|---|---|
| `requirements.txt` | Python dependencies |
| `docker-compose.yml` | PostgreSQL container definition |
| `schema.sql` | `CREATE TABLE IF NOT EXISTS` for all four PG tables |
| `db.py` | `get_mysql_conn()` and `get_pg_conn()` — reads credentials from `.env` |
| `extract.py` | `extract_table(mysql_cur, pg_cur, table, columns)` and `extract()` |
| `transform.py` | `transform(pg_conn=None)` — runs TRUNCATE + INSERT aggregation SQL |
| `pipeline.py` | `main()` — calls `extract()` then `transform()` |
| `tests/conftest.py` | `pg_conn` session-scoped fixture |
| `tests/test_connections.py` | Verifies PostgreSQL connection is reachable |
| `tests/test_extract.py` | Unit-tests `extract_table` with a mocked MySQL cursor |
| `tests/test_transform.py` | Integration-tests `transform` against known staging data |

---

## Task 1: Project Infrastructure

**Files:**
- Create: `requirements.txt`
- Create: `docker-compose.yml`
- Create: `schema.sql`
- Modify: `.env` (append PG variables)

- [ ] **Step 1: Write `requirements.txt`**

```
pymysql>=1.1.1
psycopg2-binary>=2.9.9
python-dotenv>=1.0.1
pytest>=8.3.0
```

- [ ] **Step 2: Write `docker-compose.yml`**

```yaml
services:
  postgres:
    image: postgres:16
    environment:
      POSTGRES_USER: basket_craft
      POSTGRES_PASSWORD: basket_craft
      POSTGRES_DB: basket_craft
    ports:
      - "5432:5432"
    volumes:
      - pg_data:/var/lib/postgresql/data

volumes:
  pg_data:
```

- [ ] **Step 3: Write `schema.sql`**

```sql
CREATE TABLE IF NOT EXISTS stg_orders (
    order_id            INT PRIMARY KEY,
    created_at          TIMESTAMP,
    website_session_id  INT,
    user_id             INT,
    primary_product_id  INT,
    items_purchased     SMALLINT,
    price_usd           NUMERIC(6,2),
    cogs_usd            NUMERIC(6,2)
);

CREATE TABLE IF NOT EXISTS stg_order_items (
    order_item_id   INT PRIMARY KEY,
    created_at      TIMESTAMP,
    order_id        INT,
    product_id      INT,
    is_primary_item SMALLINT,
    price_usd       NUMERIC(6,2),
    cogs_usd        NUMERIC(6,2)
);

CREATE TABLE IF NOT EXISTS stg_products (
    product_id      INT PRIMARY KEY,
    created_at      TIMESTAMP,
    product_name    VARCHAR(50),
    description     TEXT
);

CREATE TABLE IF NOT EXISTS monthly_sales (
    sale_month      DATE,
    product_id      INT,
    product_name    VARCHAR(50),
    order_count     INT,
    revenue_usd     NUMERIC(12,2),
    avg_order_value NUMERIC(10,2),
    PRIMARY KEY (sale_month, product_id)
);
```

- [ ] **Step 4: Append PG credentials to `.env`**

Add these lines to the existing `.env` (which already has MySQL vars):

```
PG_HOST=localhost
PG_PORT=5432
PG_USER=basket_craft
PG_PASSWORD=basket_craft
PG_DATABASE=basket_craft
```

- [ ] **Step 5: Install dependencies**

```bash
pip install -r requirements.txt
```

Expected: no errors, all four packages installed.

- [ ] **Step 6: Start PostgreSQL container**

```bash
docker-compose up -d
```

Expected output contains: `Container basket-craft-pipeline-postgres-1  Started`

- [ ] **Step 7: Apply schema**

```bash
docker exec -i basket-craft-pipeline-postgres-1 \
  psql -U basket_craft -d basket_craft < schema.sql
```

Expected output:
```
CREATE TABLE
CREATE TABLE
CREATE TABLE
CREATE TABLE
```

- [ ] **Step 8: Commit**

```bash
git add requirements.txt docker-compose.yml schema.sql
git commit -m "feat: add project infrastructure (docker, schema, deps)"
```

---

## Task 2: DB Connection Helpers

**Files:**
- Create: `db.py`
- Create: `tests/conftest.py`
- Create: `tests/test_connections.py`

- [ ] **Step 1: Write the failing connection test**

Create `tests/test_connections.py`:

```python
def test_pg_connection_is_reachable(pg_conn):
    with pg_conn.cursor() as cur:
        cur.execute("SELECT 1")
        result = cur.fetchone()
    assert result == (1,)
```

- [ ] **Step 2: Run it to verify it fails**

```bash
pytest tests/test_connections.py -v
```

Expected: `ERROR` — `pg_conn` fixture not found.

- [ ] **Step 3: Write `tests/conftest.py`**

```python
import os
import pytest
import psycopg2
from dotenv import load_dotenv

load_dotenv()


@pytest.fixture(scope="session")
def pg_conn():
    conn = psycopg2.connect(
        host=os.environ.get("PG_HOST", "localhost"),
        port=int(os.environ.get("PG_PORT", "5432")),
        user=os.environ["PG_USER"],
        password=os.environ["PG_PASSWORD"],
        dbname=os.environ["PG_DATABASE"],
    )
    yield conn
    conn.close()
```

- [ ] **Step 4: Write `db.py`**

```python
import os
import pymysql
import pymysql.cursors
import psycopg2
from dotenv import load_dotenv

load_dotenv()


def get_mysql_conn():
    return pymysql.connect(
        host=os.environ["MYSQL_HOST"],
        port=int(os.environ["MYSQL_PORT"]),
        user=os.environ["MYSQL_USER"],
        password=os.environ["MYSQL_PASSWORD"],
        database=os.environ["MYSQL_DATABASE"],
        cursorclass=pymysql.cursors.DictCursor,
    )


def get_pg_conn():
    return psycopg2.connect(
        host=os.environ.get("PG_HOST", "localhost"),
        port=int(os.environ.get("PG_PORT", "5432")),
        user=os.environ["PG_USER"],
        password=os.environ["PG_PASSWORD"],
        dbname=os.environ["PG_DATABASE"],
    )
```

- [ ] **Step 5: Run test to verify it passes**

```bash
pytest tests/test_connections.py -v
```

Expected: `PASSED tests/test_connections.py::test_pg_connection_is_reachable`

- [ ] **Step 6: Commit**

```bash
git add db.py tests/conftest.py tests/test_connections.py
git commit -m "feat: add db connection helpers and pg fixture"
```

---

## Task 3: Extract

**Files:**
- Create: `extract.py`
- Create: `tests/test_extract.py`

- [ ] **Step 1: Write the failing test**

Create `tests/test_extract.py`:

```python
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
```

- [ ] **Step 2: Run it to verify it fails**

```bash
pytest tests/test_extract.py -v
```

Expected: `ImportError: cannot import name 'extract_table' from 'extract'`

- [ ] **Step 3: Write `extract.py`**

```python
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
```

- [ ] **Step 4: Run test to verify it passes**

```bash
pytest tests/test_extract.py -v
```

Expected: `PASSED tests/test_extract.py::test_extract_table_truncates_and_loads_rows`

- [ ] **Step 5: Commit**

```bash
git add extract.py tests/test_extract.py
git commit -m "feat: add extract phase (MySQL -> PostgreSQL staging)"
```

---

## Task 4: Transform

**Files:**
- Create: `transform.py`
- Create: `tests/test_transform.py`

- [ ] **Step 1: Write the failing test**

Create `tests/test_transform.py`:

```python
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
```

- [ ] **Step 2: Run it to verify it fails**

```bash
pytest tests/test_transform.py -v
```

Expected: `ImportError: cannot import name 'transform' from 'transform'`

- [ ] **Step 3: Write `transform.py`**

```python
from db import get_pg_conn

_TRUNCATE = "TRUNCATE monthly_sales"

_INSERT = """
INSERT INTO monthly_sales
    (sale_month, product_id, product_name, order_count, revenue_usd, avg_order_value)
SELECT
    DATE_TRUNC('month', oi.created_at)::DATE         AS sale_month,
    p.product_id,
    p.product_name,
    COUNT(DISTINCT oi.order_id)                      AS order_count,
    SUM(oi.price_usd)                                AS revenue_usd,
    SUM(oi.price_usd) / COUNT(DISTINCT oi.order_id)  AS avg_order_value
FROM stg_order_items  oi
JOIN stg_products     p  ON p.product_id = oi.product_id
GROUP BY 1, 2, 3
ORDER BY 1, 2
"""


def transform(pg_conn=None):
    _close = pg_conn is None
    if _close:
        pg_conn = get_pg_conn()
    try:
        with pg_conn.cursor() as cur:
            cur.execute(_TRUNCATE)
            cur.execute(_INSERT)
        pg_conn.commit()
    finally:
        if _close:
            pg_conn.close()
```

- [ ] **Step 4: Run test to verify it passes**

```bash
pytest tests/test_transform.py -v
```

Expected: `PASSED tests/test_transform.py::test_transform_aggregates_by_product_and_month`

- [ ] **Step 5: Run full test suite**

```bash
pytest -v
```

Expected: all 3 tests pass (`test_connections`, `test_extract`, `test_transform`).

- [ ] **Step 6: Commit**

```bash
git add transform.py tests/test_transform.py
git commit -m "feat: add transform phase (staging -> monthly_sales)"
```

---

## Task 5: Pipeline Orchestrator

**Files:**
- Create: `pipeline.py`

- [ ] **Step 1: Write `pipeline.py`**

```python
from extract import extract
from transform import transform


def main():
    print("Extracting from MySQL into staging tables...")
    extract()
    print("Transforming staging tables into monthly_sales...")
    transform()
    print("Pipeline complete.")


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Run the full pipeline end-to-end**

```bash
python pipeline.py
```

Expected output:
```
Extracting from MySQL into staging tables...
  stg_orders: <N> rows loaded
  stg_order_items: <N> rows loaded
  stg_products: 4 rows loaded
Transforming staging tables into monthly_sales...
Pipeline complete.
```

- [ ] **Step 3: Verify `monthly_sales` has data**

```bash
docker exec -i basket-craft-pipeline-postgres-1 \
  psql -U basket_craft -d basket_craft \
  -c "SELECT sale_month, product_name, order_count, revenue_usd, avg_order_value FROM monthly_sales ORDER BY sale_month, product_id LIMIT 10;"
```

Expected: rows with `sale_month`, product names, and non-null numeric values.

- [ ] **Step 4: Run full test suite one final time**

```bash
pytest -v
```

Expected: all 3 tests pass.

- [ ] **Step 5: Commit**

```bash
git add pipeline.py
git commit -m "feat: add pipeline orchestrator and complete ELT pipeline"
```
