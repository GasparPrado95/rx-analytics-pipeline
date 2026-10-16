-- The ICB monthly aggregate must add back up to the fact table.
with fact as (
    select
        icb_code,
        date_trunc(dispensing_date, month) as month_start,
        sum(items) as items,
        round(sum(net_ingredient_cost), 2) as nic
    from {{ ref('fct_prescription_items') }}
    group by 1, 2
),

summary as (
    select
        icb_code,
        month_start,
        total_items as items,
        round(total_net_ingredient_cost, 2) as nic
    from {{ ref('mart_icb_monthly_summary') }}
)

select
    coalesce(f.icb_code, s.icb_code) as icb_code,
    coalesce(f.month_start, s.month_start) as month_start,
    f.items as fact_items,
    s.items as summary_items,
    f.nic as fact_nic,
    s.nic as summary_nic
from fact as f
full outer join summary as s on f.icb_code = s.icb_code and f.month_start = s.month_start
where f.items is null or s.items is null or f.items != s.items or abs(f.nic - s.nic) > 0.01
