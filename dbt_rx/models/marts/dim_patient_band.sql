-- Privacy by design: the marts never expose patient_id. Facts link to a band
-- (age band x sex x deprivation decile) instead of an individual.
with bands as (
    select distinct age_band, sex, imd_decile
    from {{ ref('stg_rx__patients') }}
)

select
    {{ dbt_utils.generate_surrogate_key(['age_band', 'sex', 'imd_decile']) }} as patient_band_key,
    age_band,
    case age_band
        when '0-4' then 1 when '5-14' then 2 when '15-24' then 3 when '25-44' then 4
        when '45-64' then 5 when '65-74' then 6 when '75-84' then 7 when '85+' then 8
    end as age_band_order,
    case when age_band in ('65-74', '75-84', '85+') then '65 and over' else 'Under 65' end as age_group,
    sex,
    case sex when 'F' then 'Female' when 'M' then 'Male' else 'Unknown' end as sex_label,
    imd_decile,
    coalesce(cast(imd_decile as string), 'Unknown') as imd_decile_label
from bands
