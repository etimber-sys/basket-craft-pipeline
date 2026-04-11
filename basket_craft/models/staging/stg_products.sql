select
    product_id,
    product_name,
    description                 as product_description,
    created_at::timestamp_ntz   as product_added_at
from {{ source('raw', 'products') }}
