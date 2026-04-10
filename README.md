# Basket Craft Sales Pipeline

An ELT pipeline that extracts sales data from the Basket Craft MySQL database, loads it into a local PostgreSQL instance, and transforms it into a `monthly_sales` fact table for dashboard reporting.

**Dashboard metrics produced:**
- Revenue by product and month
- Order count by product and month
- Average order value by product and month

## How it works

```
MySQL (db.isba.co)          PostgreSQL (Docker)
──────────────────          ───────────────────
  orders          ────────► stg_orders
  order_items     ────────► stg_order_items       monthly_sales
  products        ────────► stg_products    ─SQL─► (fact table)
```

Each run does a full refresh: staging and fact tables are truncated and repopulated from scratch. The pipeline is triggered manually by running `python pipeline.py`.

## Prerequisites

- Python 3.x
- Docker Desktop (for the local PostgreSQL instance)
- Access to the Basket Craft MySQL database

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

PG_HOST=localhost
PG_PORT=5432
PG_USER=basket_craft
PG_PASSWORD=basket_craft
PG_DATABASE=basket_craft
```

**3. Start PostgreSQL**

```bash
docker compose up -d
```

**4. Initialize the schema** (run once after first `docker compose up`)

```bash
psql -U basket_craft -d basket_craft -f schema.sql
```

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

Tests require the PostgreSQL Docker container to be running. MySQL is not needed — the MySQL layer is mocked.

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
