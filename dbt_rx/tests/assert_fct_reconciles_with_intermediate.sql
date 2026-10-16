-- The incremental fact must match a full recomputation from the intermediate layer:
-- same number of lines, items and cost. Catches drift from missed or double-applied merges.
with expected as (
    select
        count(*) as lines,
        sum(case when is_credit then -items else items end) as items,
        round(sum(net_ingredient_cost_filled), 2) as nic
    from {{ ref('int_prescription_items__priced') }}
    where not is_duplicate_submission
),

actual as (
    select count(*) as lines, sum(items) as items, round(sum(net_ingredient_cost), 2) as nic
    from {{ ref('fct_prescription_items') }}
)

select e.*, a.lines as fact_lines, a.items as fact_items, a.nic as fact_nic
from expected as e
cross join actual as a
where e.lines != a.lines or e.items != a.items or abs(e.nic - a.nic) > 0.01
