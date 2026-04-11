select
    user_id                     as customer_id,
    created_at::timestamp_ntz   as customer_created_at,
    first_name,
    last_name,
    email
from {{ source('raw', 'customers') }}
