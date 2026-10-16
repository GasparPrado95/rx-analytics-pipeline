-- Open-ended rows get a far-future end date so "price at date" is a simple BETWEEN join.
select
    presentation_code,
    effective_from,
    coalesce(effective_to, date '9999-12-31') as effective_to,
    effective_to is null as is_current,
    unit_cost,
    change_reason
from {{ source('rx', 'medicine_price_history') }}
