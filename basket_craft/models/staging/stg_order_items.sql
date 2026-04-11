select
    order_item_id,
    order_id,
    product_id,
    created_at::timestamp_ntz   as ordered_at,
    is_primary_item::boolean    as is_primary_item,
    price_usd                   as item_revenue_usd,
    cogs_usd                    as item_cost_usd
from {{ source('raw', 'order_items') }}
