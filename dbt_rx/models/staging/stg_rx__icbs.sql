select
    icb_code,
    trim(icb_name) as icb_name,
    region_code
from {{ source('rx', 'icb') }}
