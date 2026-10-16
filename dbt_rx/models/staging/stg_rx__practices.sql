-- Normalises the practice feed's free-text fields (casing / whitespace defects in the source).
select
    practice_code,
    trim(practice_name) as practice_name,
    icb_code,
    nullif(upper(trim(postcode_district)), '') as postcode_district,
    regexp_extract(upper(trim(postcode_district)), r'^[A-Z]+') as postcode_area,
    list_size,
    initcap(trim(rural_urban)) as rural_urban,
    rural_urban != initcap(trim(rural_urban)) as is_rural_urban_nonstandard,
    imd_decile as practice_imd_decile,
    opened_date,
    updated_at
from {{ source('rx', 'practice') }}
