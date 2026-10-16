-- 1:1 with the source line table: rename/cast and dedupe on the primary key only.
-- Business rules (double submissions, imputation, credits) live in the intermediate layer.
select
    item_line_id,
    prescription_id,
    presentation_code,
    cast(items as int64) as items,
    quantity,
    net_ingredient_cost,
    actual_cost,
    dispensing_date,
    created_at,
    updated_at
from {{ source('rx', 'prescription_item') }}
qualify row_number() over (partition by item_line_id order by updated_at desc) = 1
