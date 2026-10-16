-- Flags line-level data-quality conditions without dropping anything, so the DQ mart can count them.
--   is_duplicate_submission: same prescription, presentation and dispensing date as an earlier-arriving
--                            line (a double submission under a new id). The key deliberately leaves out
--                            quantity and cost: a later correction of either copy must not flip which
--                            line counts, or the incremental fact and a full rebuild would disagree.
--   is_late_arrival:         reached the source more than `late_arrival_days` after dispensing.
--   is_restated:             corrected after it first arrived (updated_at moved on).
select
    *,
    row_number() over (
        partition by prescription_id, presentation_code, dispensing_date
        order by created_at, item_line_id
    ) > 1 as is_duplicate_submission,
    date_diff(date(created_at), dispensing_date, day) as arrival_lag_days,
    date_diff(date(created_at), dispensing_date, day) > {{ var('late_arrival_days') }} as is_late_arrival,
    updated_at > created_at as is_restated,
    coalesce(quantity, 0) < 0 or coalesce(net_ingredient_cost, 0) < 0 as is_credit
from {{ ref('stg_rx__prescription_items') }}
