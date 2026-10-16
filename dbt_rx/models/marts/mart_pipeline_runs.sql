-- EL run history for the pipeline-health page: one row per table per run, with run-level rollups.
select
    {{ dbt_utils.generate_surrogate_key(['run_id', 'table_name']) }} as run_table_key,
    run_id,
    table_name,
    load_mode,
    status,
    is_full_refresh,
    rows_loaded,
    watermark_before,
    watermark_after,
    started_at,
    finished_at,
    duration_seconds,
    error_message,
    date(started_at) as run_date,
    logical_and(status = 'success') over (partition by run_id) as run_succeeded,
    sum(rows_loaded) over (partition by run_id) as run_rows_loaded,
    count(*) over (partition by run_id) as run_tables,
    max(started_at) over () = started_at as is_latest_run
from {{ ref('stg_rx__el_run_log') }}
