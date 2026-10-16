select
    region_code,
    ons_code as region_ons_code,
    trim(region_name) as region_name
from {{ source('rx', 'region') }}
