select
    prescriber_id,
    prescriber_code,
    prescriber_type_code,
    practice_code,
    concat(trim(first_name), ' ', trim(last_name)) as prescriber_name,
    start_date,
    updated_at
from {{ source('rx', 'prescriber') }}
