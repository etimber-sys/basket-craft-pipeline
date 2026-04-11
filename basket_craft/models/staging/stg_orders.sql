select
    order_id,
    user_id                     as customer_id,
    website_session_id,
    primary_product_id,
    created_at::timestamp_ntz   as ordered_at,
    items_purchased,
    price_usd                   as order_revenue_usd,
    cogs_usd                    as order_cost_usd
from {{ source('raw', 'orders') }}
