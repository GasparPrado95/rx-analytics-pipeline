-- Double submissions (same prescription, medicine and dispensing date under a new id) must never
-- reach the fact, including ones that arrive in a later incremental batch.
select prescription_id, presentation_code, dispensing_date, count(*) as lines
from {{ ref('fct_prescription_items') }}
group by prescription_id, presentation_code, dispensing_date
having count(*) > 1
