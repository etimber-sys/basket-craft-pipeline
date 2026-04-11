# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Environment Setup

Use a Python virtual environment to manage dependencies:

```bash
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

Copy `.env.example` to `.env` (or create `.env`) and fill in credentials — see the **Environment Variables** section below.

## Common Commands

```bash
# Start PostgreSQL (required for tests and pipeline runs)
docker compose up -d

# Initialize the PostgreSQL schema (run once after first docker compose up)
psql -U basket_craft -d basket_craft -f schema.sql

# Run the full ELT pipeline
python pipeline.py

# Run all tests
pytest

# Run a single test
pytest tests/test_transform.py::test_transform_aggregates_by_product_and_month
```

## Architecture

This is a manual ELT pipeline that moves Basket Craft sales data from MySQL into PostgreSQL for dashboard reporting.

```
MySQL (db.isba.co)          PostgreSQL (Docker)
──────────────────          ───────────────────
  orders          ────────► stg_orders
  order_items     ────────► stg_order_items       monthly_sales
  products        ────────► stg_products    ─SQL─► (fact table)
```

**Load strategy:** Full refresh — every run TRUNCATEs then re-inserts all rows. No incremental logic.

### Module responsibilities

| File | Role |
|------|------|
| `pipeline.py` | Entry point — calls `extract()` then `transform()` |
| `extract.py` | Reads each table from MySQL via `pymysql`, batch-inserts into `stg_*` tables in PostgreSQL. Table/column names come from the `TABLES` constant (developer-controlled, never user input). |
| `transform.py` | Runs a single aggregation SQL query inside PostgreSQL: `stg_order_items JOIN stg_products → monthly_sales`. |
| `db.py` | Connection factories `get_mysql_conn()` / `get_pg_conn()`. Reads credentials from env vars; raises `EnvironmentError` on missing required vars. |
| `schema.sql` | `CREATE TABLE IF NOT EXISTS` for all staging and fact tables. Run once to set up a fresh PostgreSQL instance. |

### Key design decisions

- `transform(pg_conn=None)` accepts an optional connection so tests can inject a fixture connection and inspect results before commit. When `None`, it opens and closes its own connection.
- Extract batches inserts in groups of 1,000 rows (`BATCH_SIZE`). For larger datasets, consider switching to `SSCursor` + `fetchmany()` instead of `fetchall()`.
- Both `extract()` and `transform()` roll back the PostgreSQL transaction on failure, leaving tables in their last known good state.

## Testing

Tests are **integration tests against a real PostgreSQL instance** (Docker). MySQL is never required — the MySQL cursor is mocked with `MagicMock` in extract tests.

The `pg_conn` fixture in `conftest.py` is session-scoped (one connection for all tests). Each test is responsible for cleaning up staging table state before use.

## dbt Project

The dbt project lives at `basket_craft/` inside this repo. All dbt commands must be run from that directory.

### Running dbt

```bash
cd basket_craft

# Run all models
../venv/Scripts/dbt run          # Windows
../venv/bin/dbt run              # Mac/Linux

# Run tests (generic tests declared in schema YAML files)
../venv/Scripts/dbt test         # Windows
../venv/bin/dbt test             # Mac/Linux

# Generate and serve docs
../venv/Scripts/dbt docs generate
../venv/Scripts/dbt docs serve   # opens at http://localhost:8080
```

### Profile configuration

`~/.dbt/profiles.yml` lives **outside the repo** and is not committed. It reads all credentials from environment variables, which must be present in `.env` and sourced before running dbt:

```bash
set -a && source ../.env && set +a
```

The profile name is `basket_craft`, target `dev`, adapter `snowflake`.

### Models

**Staging** (`models/staging/`) — views over raw Snowflake source tables:

| Model | Source table |
|-------|-------------|
| `stg_orders` | `raw.orders` |
| `stg_order_items` | `raw.order_items` |
| `stg_products` | `raw.products` |
| `stg_customers` | `raw.customers` |

**Marts** (`models/marts/`) — materialized as tables:

| Model | Description |
|-------|-------------|
| `fct_order_items` | One row per order line item; grain is `order_item_id` |
| `dim_products` | Product reference dimension |
| `dim_customers` | Customer dimension (requires `raw.customers` in Snowflake) |
| `dim_date` | Date spine derived from the min/max order dates in `stg_orders` |

Schema tests are declared in `models/marts/_schema.yml`. `fct_order_items.order_item_id` is tested for `unique` and `not_null`.

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
| `PG_HOST` | Optional, defaults to `localhost` |
| `PG_PORT` | Optional, defaults to `5432` |
| `SNOWFLAKE_ACCOUNT` | Used by dbt profile |
| `SNOWFLAKE_USER` | Used by dbt profile |
| `SNOWFLAKE_PASSWORD` | Used by dbt profile |
| `SNOWFLAKE_ROLE` | Used by dbt profile |
| `SNOWFLAKE_WAREHOUSE` | Used by dbt profile |
| `SNOWFLAKE_DATABASE` | Used by dbt profile |

