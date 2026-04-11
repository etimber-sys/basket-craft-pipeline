{{ config(materialized='table') }}

select
    product_id,
    product_name,
    product_description,
    product_added_at
from {{ ref('stg_products') }}
