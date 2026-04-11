# RDS to Snowflake Load — Design Spec

**Date:** 2026-04-10
**Status:** Approved

---

## Overview

A standalone script (`load_snowflake.py`) that reads the three raw Basket Craft tables from AWS RDS PostgreSQL and loads them into the `basket_craft.raw` schema in Snowflake. Full refresh on every run — TRUNCATE then reload. Runs independently of `pipeline.py`.

---

## Architecture

```
AWS RDS PostgreSQL           Snowflake
─────────────────            ─────────────────────────
  stg_orders      ─────────► basket_craft.raw.orders
  stg_order_items ─────────► basket_craft.raw.order_items
  stg_products    ─────────► basket_craft.raw.products
```

**Load strategy:** Full refresh — TRUNCATE each Snowflake target table, then batch INSERT all rows from RDS (batch size: 1,000 rows, consistent with `extract.py`).

**Trigger:** Manual — `python load_snowflake.py`

---

## File Layout

One new file added to the existing repo:

```
basket-craft-pipeline/
├── load_snowflake.py     ← NEW
├── pipeline.py           ← unchanged
├── extract.py            ← unchanged
├── transform.py          ← unchanged
├── db.py                 ← unchanged (get_pg_conn() reused)
├── schema.sql            ← unchanged
└── requirements.txt      ← add snowflake-connector-python
```

---

## Table Mapping

| RDS (source) | Snowflake (target) |
|---|---|
| `stg_orders` | `basket_craft.raw.orders` |
| `stg_order_items` | `basket_craft.raw.order_items` |
| `stg_products` | `basket_craft.raw.products` |

The `stg_` prefix is dropped in Snowflake. Column names and types are preserved as-is.

---

## Credentials

Six new variables added to `.env`:

```
SNOWFLAKE_ACCOUNT=your_account_identifier
SNOWFLAKE_USER=your_username
SNOWFLAKE_PASSWORD=your_password
SNOWFLAKE_WAREHOUSE=your_warehouse
SNOWFLAKE_DATABASE=basket_craft
SNOWFLAKE_SCHEMA=raw
```

`load_snowflake.py` loads these via `python-dotenv` (already a dependency). The RDS connection is opened via `get_pg_conn()` from `db.py`. The Snowflake connection is opened via `snowflake.connector.connect()` — both closed in a `finally` block. No changes to `db.py` — Snowflake connection logic lives entirely in `load_snowflake.py`.

---

## Load Logic

For each table in order (`orders`, `order_items`, `products`):

1. `SELECT *` from the RDS staging table using `psycopg2`
2. `TRUNCATE` the Snowflake target table
3. Batch INSERT rows using `executemany` (1,000 rows/batch)
4. Print row count on success

Tables are processed sequentially. The Snowflake connection commits explicitly after each table completes.

---

## Error Handling

- Connection failure (RDS or Snowflake) raises immediately with a descriptive message
- Failure on any table halts the run — subsequent tables are not touched
- TRUNCATE occurs immediately before INSERT for each table; a mid-run crash leaves that table empty and previously completed tables intact
- No retries — script is manual; user re-runs on failure

---

## Output

```
Loading orders into Snowflake...
  orders: 32,313 rows loaded
Loading order_items into Snowflake...
  order_items: 54,721 rows loaded
Loading products into Snowflake...
  products: 4 rows loaded
Done.
```

---

## Testing

No automated tests. The logic is a thin read-from-RDS / write-to-Snowflake adapter with no branching or transformation. Correctness is verified by running the script and confirming printed row counts match RDS.

---

## Environment Variables Added

| Variable | Notes |
|---|---|
| `SNOWFLAKE_ACCOUNT` | Account identifier (e.g. `xy12345.us-east-1`) |
| `SNOWFLAKE_USER` | Snowflake username |
| `SNOWFLAKE_PASSWORD` | Snowflake password |
| `SNOWFLAKE_WAREHOUSE` | Warehouse to use for the load |
| `SNOWFLAKE_DATABASE` | Target database — `basket_craft` |
| `SNOWFLAKE_SCHEMA` | Target schema — `raw` |
