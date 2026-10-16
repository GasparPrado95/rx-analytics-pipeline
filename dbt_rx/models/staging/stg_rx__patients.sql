-- Sex codes arrive in mixed case; anything other than F/M becomes U (unknown).
select
    patient_id,
    practice_code,
    age_band,
    case upper(trim(sex)) when 'F' then 'F' when 'M' then 'M' else 'U' end as sex,
    sex not in ('F', 'M') as is_sex_code_nonstandard,
    imd_decile,
    registered_date,
    updated_at
from {{ source('rx', 'patient') }}
