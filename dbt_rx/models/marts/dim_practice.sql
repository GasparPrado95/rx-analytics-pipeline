select
    practice_code,
    practice_name,
    postcode_district,
    postcode_area,
    'United Kingdom' as country,  -- helps map visuals geocode the postcode district
    list_size,
    registered_patients,
    rural_urban,
    practice_imd_decile,
    case
        when practice_imd_decile <= 2 then '1 - Most deprived'
        when practice_imd_decile <= 4 then '2'
        when practice_imd_decile <= 6 then '3'
        when practice_imd_decile <= 8 then '4'
        else '5 - Least deprived'
    end as practice_imd_quintile,
    opened_date,
    icb_code,
    icb_name,
    region_code,
    region_ons_code,
    region_name
from {{ ref('int_practices__enriched') }}
