{{ config(materialized='table') }}

with order_items as (
    select * from {{ ref('stg_order_items') }}
),

orders as (
    select * from {{ ref('stg_orders') }}
)

select
    -- keys
    oi.order_item_id,
    oi.order_id,
    oi.product_id,
    o.customer_id,
    oi.ordered_at::date     as order_date,       -- FK to dim_date.date_day

    -- attributes
    oi.is_primary_item,
    o.website_session_id,

    -- measures
    1                       as quantity,
    oi.item_revenue_usd     as unit_price,
    oi.item_cost_usd        as unit_cost,
    1 * oi.item_revenue_usd as line_total,

    -- timestamps
    oi.ordered_at
from order_items oi
inner join orders o on o.order_id = oi.order_id
