# Basket Craft Sales Pipeline

An ELT pipeline that extracts sales data from the Basket Craft MySQL database, loads it into PostgreSQL, and transforms it into a `monthly_sales` fact table for dashboard reporting.

**Dashboard metrics produced:**
- Revenue by product and month
- Order count by product and month
- Average order value by product and month

## How it works

```
MySQL (db.isba.co)          PostgreSQL
──────────────────          ──────────
  orders          ────────► stg_orders
  order_items     ────────► stg_order_items       monthly_sales
  products        ────────► stg_products    ─SQL─► (fact table)
```

Each run does a full refresh: staging and fact tables are truncated and repopulated from scratch. The pipeline is triggered manually by running `python pipeline.py`.

## AWS RDS PostgreSQL

The project includes an AWS RDS PostgreSQL instance pre-loaded with raw Basket Craft data.

| Setting | Value |
|---------|-------|
| Instance | `basket-craft-db` |
| Engine | PostgreSQL 17.6 |
| Host | `basket-craft-db.canqgqm8gu16.us-east-1.rds.amazonaws.com` |
| Port | `5432` |
| Database | `basket_craft` |
| Instance class | `db.t3.micro` (free tier) |

To run the pipeline against RDS, set `PG_HOST` in `.env` to the host above.

## Prerequisites

- Python 3.x
- Access to the Basket Craft MySQL database
- Docker Desktop (optional — for running a local PostgreSQL instance instead of RDS)

## Setup

**1. Clone the repo and create a virtual environment**

```bash
git clone <repo-url>
cd basket-craft-pipeline
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

**2. Configure environment variables**

Create a `.env` file in the project root:

```
MYSQL_HOST=db.isba.co
MYSQL_PORT=3306
MYSQL_USER=your_username
MYSQL_PASSWORD=your_password
MYSQL_DATABASE=basket_craft

# Use the RDS endpoint for production, or localhost for local Docker
PG_HOST=basket-craft-db.canqgqm8gu16.us-east-1.rds.amazonaws.com
PG_PORT=5432
PG_USER=student
PG_PASSWORD=your_password
PG_DATABASE=basket_craft
```

**3. (Optional) Run against a local PostgreSQL instead of RDS**

```bash
docker compose up -d
psql -U basket_craft -d basket_craft -f schema.sql
```

Then set `PG_HOST=localhost` in `.env`.

## Running the pipeline

```bash
python pipeline.py
```

Output:

```
Extracting from MySQL into staging tables...
  stg_orders: 32313 rows loaded
  stg_order_items: 54721 rows loaded
  stg_products: 4 rows loaded
Transforming staging tables into monthly_sales...
Pipeline complete.
```

## Running tests

Tests require a running PostgreSQL instance (local Docker recommended — point `PG_HOST=localhost`). MySQL is not needed — the MySQL layer is mocked.

```bash
pytest
```

## Project structure

```
basket-craft-pipeline/
├── pipeline.py       # Entry point — calls extract() then transform()
├── extract.py        # MySQL → PostgreSQL staging tables
├── transform.py      # Staging tables → monthly_sales fact table (SQL aggregation)
├── db.py             # Connection factories (reads credentials from .env)
├── schema.sql        # PostgreSQL table definitions — run once to initialize
├── docker-compose.yml
├── requirements.txt
└── tests/
    ├── conftest.py         # pg_conn session fixture
    ├── test_connections.py
    ├── test_extract.py
    └── test_transform.py
```
