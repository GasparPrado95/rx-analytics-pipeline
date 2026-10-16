-- Defensive dedupe on the primary key (latest version wins), e.g. if a load is ever replayed.
select
    prescription_id,
    patient_id,
    prescriber_id,
    practice_code,
    issue_date,
    created_at,
    updated_at
from {{ source('rx', 'prescription') }}
qualify row_number() over (partition by prescription_id order by updated_at desc) = 1
