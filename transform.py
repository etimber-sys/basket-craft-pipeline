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
    """Aggregate stg_order_items + stg_products into monthly_sales.

    Truncates monthly_sales then inserts aggregated rows grouped by product
    and month. Metrics: revenue (SUM price_usd), order_count (COUNT DISTINCT
    order_id), avg_order_value (revenue / order_count).

    If pg_conn is None, opens and closes its own connection (pipeline mode).
    Pass an existing connection to reuse it without closing (test mode).
    """
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
