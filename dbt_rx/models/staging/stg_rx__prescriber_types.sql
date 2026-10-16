select
    prescriber_type_code,
    prescriber_type_name
from {{ source('rx', 'prescriber_type') }}
