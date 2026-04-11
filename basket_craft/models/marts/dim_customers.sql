{{ config(materialized='table') }}

select
    customer_id,
    first_name,
    last_name,
    email,
    customer_created_at
from {{ ref('stg_customers') }}
