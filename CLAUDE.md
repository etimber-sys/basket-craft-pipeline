# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Environment Setup

Use a Python virtual environment to manage dependencies:

```bash
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

Create a `.env` file in the project root (no `.env.example` exists — create it from scratch):

```
MYSQL_HOST=db.isba.co
MYSQL_PORT=3306
MYSQL_USER=your_username
MYSQL_PASSWORD=your_password
MYSQL_DATABASE=basket_craft

PG_HOST=localhost          # or RDS endpoint for production runs
PG_PORT=5432
PG_USER=basket_craft
PG_PASSWORD=basket_craft
PG_DATABASE=basket_craft

SNOWFLAKE_ACCOUNT=your_account_identifier
SNOWFLAKE_USER=your_username
SNOWFLAKE_PASSWORD=your_password
SNOWFLAKE_ROLE=your_role
SNOWFLAKE_WAREHOUSE=your_warehouse
SNOWFLAKE_DATABASE=basket_craft
SNOWFLAKE_SCHEMA=raw
```

## Common Commands

```bash
# Start local PostgreSQL (required for tests; not needed when PG_HOST points to RDS)
docker compose up -d

# Initialize the PostgreSQL schema (run once on a fresh instance)
psql -U basket_craft -d basket_craft -f schema.sql

# Run the full ELT pipeline (MySQL → RDS PostgreSQL)
python pipeline.py

# Load raw tables from RDS into Snowflake (basket_craft.raw)
python load_snowflake.py

# Run all tests
pytest

# Run a single test
pytest tests/test_transform.py::test_transform_aggregates_by_product_and_month
```

## Architecture

Manual ELT pipeline: Basket Craft MySQL → PostgreSQL staging → `monthly_sales` fact table.

```
MySQL (db.isba.co)     PostgreSQL (Docker or RDS)     Snowflake (basket_craft.raw)
──────────────────     ──────────────────────────     ────────────────────────────
  orders         ────► stg_orders              ─────► orders
  order_items    ────► stg_order_items  ──┐    ─────► order_items
  products       ────► stg_products    ──┴─SQL─► monthly_sales
                                                ─────► products
```

`pipeline.py` handles the MySQL → PostgreSQL leg. `load_snowflake.py` handles the PostgreSQL → Snowflake leg and runs independently.

**Load strategy:** Full refresh — every run TRUNCATEs then re-inserts all rows. No incremental logic.

Expected row counts (from production MySQL): ~32K orders, ~54K order_items, 4 products.

### Module responsibilities

| File | Role |
|------|------|
| `pipeline.py` | Entry point — calls `extract()` then `transform()` |
| `extract.py` | Reads each table from MySQL via `pymysql`, batch-inserts into `stg_*` tables in PostgreSQL. Table/column names come from the `TABLES` constant (developer-controlled, never user input). |
| `transform.py` | Runs a single aggregation SQL query inside PostgreSQL: `stg_order_items JOIN stg_products → monthly_sales`. |
| `db.py` | Connection factories `get_mysql_conn()` / `get_pg_conn()`. Reads credentials from env vars; raises `EnvironmentError` on missing required vars. |
| `schema.sql` | `CREATE TABLE IF NOT EXISTS` for all staging and fact tables. Run once to set up a fresh PostgreSQL instance. |
| `load_snowflake.py` | Reads `stg_orders`, `stg_order_items`, `stg_products` from RDS and bulk-loads them into `basket_craft.raw` in Snowflake via `write_pandas`. Tables are created automatically on first run (`auto_create_table=True`). Full refresh on every run (`overwrite=True`). Credentials read from `.env` (`SNOWFLAKE_*` vars). |

### Key design decisions

- `transform(pg_conn=None)` accepts an optional connection so tests can inject a fixture connection and inspect results before commit. When `None`, it opens and closes its own connection.
- Extract batches inserts in groups of 1,000 rows (`BATCH_SIZE`). For larger datasets, consider switching to `SSCursor` + `fetchmany()` instead of `fetchall()`.
- Both `extract()` and `transform()` roll back the PostgreSQL transaction on failure, leaving tables in their last known good state.
- `monthly_sales.sale_month` is always the first day of the month (`DATE_TRUNC('month', ...)::DATE`). Revenue uses `stg_order_items.price_usd`, not `stg_orders.price_usd`.
- `stg_orders` is extracted and available for ad-hoc queries but is **not joined** in the transform — `monthly_sales` is derived from `stg_order_items + stg_products` only.

## Testing

Tests are **integration tests against a real PostgreSQL instance** (Docker or RDS). MySQL is never required — the MySQL cursor is mocked with `MagicMock` in extract tests.

The `pg_conn` fixture in `conftest.py` is session-scoped (one connection for all tests). Each test is responsible for cleaning up staging table state **before** use via `TRUNCATE` (not in teardown — tables may be dirty at test start).

**Do not import from `db.py` in `conftest.py`.** The connection logic is intentionally duplicated there to avoid pulling in `pymysql` as a test dependency — tests only need `psycopg2`.

## Environment Variables

Required in `.env`:

| Variable | Notes |
|----------|-------|
| `MYSQL_HOST` | Source database host |
| `MYSQL_PORT` | Source database port |
| `MYSQL_USER` | |
| `MYSQL_PASSWORD` | |
| `MYSQL_DATABASE` | |
| `PG_USER` | |
| `PG_PASSWORD` | |
| `PG_DATABASE` | |
| `PG_HOST` | Optional, defaults to `localhost`. Set to RDS endpoint for production pipeline runs. |
| `PG_PORT` | Optional, defaults to `5432` |
| `SNOWFLAKE_ACCOUNT` | Account identifier (e.g. `xy12345.us-east-1`) — found in your Snowflake login URL |
| `SNOWFLAKE_USER` | Snowflake username |
| `SNOWFLAKE_PASSWORD` | Snowflake password |
| `SNOWFLAKE_ROLE` | Snowflake role (e.g. `ACCOUNTADMIN`) |
| `SNOWFLAKE_WAREHOUSE` | Warehouse used for the load |
| `SNOWFLAKE_DATABASE` | Target database — `basket_craft` |
| `SNOWFLAKE_SCHEMA` | Target schema — `raw` |
