select
    p.prescriber_id,
    p.prescriber_code,
    p.prescriber_name,
    p.prescriber_type_code,
    t.prescriber_type_name,
    p.practice_code,
    p.start_date
from {{ ref('stg_rx__prescribers') }} as p
inner join {{ ref('stg_rx__prescriber_types') }} as t on t.prescriber_type_code = p.prescriber_type_code
