select
    run_id,
    table_name,
    load_mode,
    status,
    full_refresh as is_full_refresh,
    rows_loaded,
    watermark_before,
    watermark_after,
    started_at,
    finished_at,
    timestamp_diff(finished_at, started_at, second) as duration_seconds,
    error_message
from {{ source('rx', 'el_run_log') }}
qualify row_number() over (partition by run_id, table_name order by finished_at desc) = 1
