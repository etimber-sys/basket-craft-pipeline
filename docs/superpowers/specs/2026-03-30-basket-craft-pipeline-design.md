# Basket Craft Sales Pipeline — Design Spec

**Date:** 2026-03-30
**Status:** Approved

---

## Overview

An ELT pipeline that extracts sales data from the Basket Craft MySQL database, loads it into a local PostgreSQL instance (Docker), and transforms it into a `monthly_sales` fact table for the monthly sales dashboard.

**Dashboard metrics:**
- Revenue by product and month
- Order count by product and month
- Average order value by product and month

---

## Source Schema (MySQL — `basket_craft`)

Relevant tables:

| Table | Key Columns |
|---|---|
| `orders` | `order_id`, `created_at`, `user_id`, `price_usd`, `cogs_usd`, `items_purchased` |
| `order_items` | `order_item_id`, `created_at`, `order_id`, `product_id`, `price_usd`, `cogs_usd` |
| `products` | `product_id`, `product_name`, `description` |

There are 4 products (Original, Valentine's, Birthday, Holiday gift baskets). There is no `category` column — each product serves as its own category.

Tables not extracted by this pipeline: `users`, `website_sessions`, `website_pageviews`, `employees`, `order_item_refunds`.

---

## Architecture

```
MySQL (db.isba.co)                 PostgreSQL (Docker)
─────────────────                  ───────────────────
  orders          ──────────────►  stg_orders
  order_items     ──────────────►  stg_order_items
  products        ──────────────►  stg_products
                                        │
                                        │  SQL aggregation
                                        ▼
                                   monthly_sales  ◄── dashboard reads here
```

**Pattern:** ELT — raw data lands in PostgreSQL staging tables first; all transformation happens inside PostgreSQL via SQL.

**Trigger:** Manual — `python pipeline.py`

**Load strategy:** Full refresh — staging and fact tables are TRUNCATEd before each run.

---

## File Layout

```
basket-craft-pipeline/
├── .env                  ← credentials (gitignored)
├── pipeline.py           ← entry point; calls extract() then transform()
├── extract.py            ← MySQL → PostgreSQL staging (pymysql + psycopg2)
├── transform.py          ← runs aggregation SQL inside PostgreSQL
├── schema.sql            ← CREATE TABLE statements; run once to set up PG
└── requirements.txt      ← pymysql, psycopg2-binary, python-dotenv
```

---

## Target Schema (PostgreSQL)

### Staging tables (mirrors of MySQL source)

```sql
CREATE TABLE stg_orders (
    order_id            INT PRIMARY KEY,
    created_at          TIMESTAMP,
    website_session_id  INT,
    user_id             INT,
    primary_product_id  INT,
    items_purchased     SMALLINT,
    price_usd           NUMERIC(6,2),
    cogs_usd            NUMERIC(6,2)
);

CREATE TABLE stg_order_items (
    order_item_id   INT PRIMARY KEY,
    created_at      TIMESTAMP,
    order_id        INT,
    product_id      INT,
    is_primary_item SMALLINT,
    price_usd       NUMERIC(6,2),
    cogs_usd        NUMERIC(6,2)
);

CREATE TABLE stg_products (
    product_id      INT PRIMARY KEY,
    created_at      TIMESTAMP,
    product_name    VARCHAR(50),
    description     TEXT
);
```

### Fact table

```sql
CREATE TABLE monthly_sales (
    sale_month      DATE,           -- first day of month, e.g. 2024-01-01
    product_id      INT,
    product_name    VARCHAR(50),
    order_count     INT,            -- COUNT(DISTINCT order_id) for this product
    revenue_usd     NUMERIC(12,2),  -- SUM(order_items.price_usd) for this product
    avg_order_value NUMERIC(10,2),  -- revenue_usd / order_count
    PRIMARY KEY (sale_month, product_id)
);
```

---

## Transform Query

```sql
TRUNCATE monthly_sales;

INSERT INTO monthly_sales (sale_month, product_id, product_name,
                           order_count, revenue_usd, avg_order_value)
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
ORDER BY 1, 2;
```

**Metric definitions:**
- `revenue_usd` — sum of line-item prices for this product in this month
- `order_count` — number of distinct orders that included this product
- `avg_order_value` — average amount spent on this product per order (not average total cart value)

---

## Extract Logic

For each of `orders`, `order_items`, `products`:
1. `SELECT *` from MySQL table
2. `TRUNCATE stg_<table>` in PostgreSQL
3. Batch-insert rows (batch size: 1,000) using `executemany`

---

## Error Handling

- MySQL or PostgreSQL connection failure → raise immediately with a descriptive message
- Extract and transform run sequentially; any failure halts the run
- No retries — pipeline is manual; the user re-runs on failure
- A failed run leaves staging/fact tables in their previous good state (TRUNCATE happens at start of each phase, so a crash mid-insert leaves an empty table, not corrupted data)

---

## Environment Variables (`.env`)

| Variable | Purpose |
|---|---|
| `MYSQL_HOST` | MySQL hostname |
| `MYSQL_PORT` | MySQL port |
| `MYSQL_USER` | MySQL username |
| `MYSQL_PASSWORD` | MySQL password |
| `MYSQL_DATABASE` | MySQL database name |
| `PG_HOST` | PostgreSQL hostname (default: localhost) |
| `PG_PORT` | PostgreSQL port (default: 5432) |
| `PG_USER` | PostgreSQL username |
| `PG_PASSWORD` | PostgreSQL password |
| `PG_DATABASE` | PostgreSQL database name |
