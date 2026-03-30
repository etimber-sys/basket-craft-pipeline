CREATE TABLE IF NOT EXISTS stg_orders (
    order_id            INT PRIMARY KEY,
    created_at          TIMESTAMP,
    website_session_id  INT,
    user_id             INT,
    primary_product_id  INT,
    items_purchased     SMALLINT,
    price_usd           NUMERIC(10,2),
    cogs_usd            NUMERIC(10,2)
);

CREATE TABLE IF NOT EXISTS stg_order_items (
    order_item_id   INT PRIMARY KEY,
    created_at      TIMESTAMP,
    order_id        INT,
    product_id      INT,
    is_primary_item SMALLINT,
    price_usd       NUMERIC(10,2),
    cogs_usd        NUMERIC(10,2)
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
