-- Practice -> ICB -> region, flattened, with the size of the simulated patient panel.
-- The generator simulates prescribing for a sampled panel of patients per practice (50k in total),
-- while list_size is the full registered list (~3.7M). Per-patient rates must use the panel.
with panels as (
    select
        practice_code,
        count(*) as registered_patients
    from {{ ref('stg_rx__patients') }}
    group by practice_code
)

select
    p.practice_code,
    p.practice_name,
    p.postcode_district,
    p.postcode_area,
    p.list_size,
    coalesce(pn.registered_patients, 0) as registered_patients,
    p.rural_urban,
    p.is_rural_urban_nonstandard,
    p.practice_imd_decile,
    p.opened_date,
    i.icb_code,
    i.icb_name,
    r.region_code,
    r.region_ons_code,
    r.region_name
from {{ ref('stg_rx__practices') }} as p
inner join {{ ref('stg_rx__icbs') }} as i on p.icb_code = i.icb_code
inner join {{ ref('stg_rx__regions') }} as r on i.region_code = r.region_code
left join panels as pn on p.practice_code = pn.practice_code
