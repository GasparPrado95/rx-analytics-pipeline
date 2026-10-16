{{
    config(
        materialized='incremental',
        incremental_strategy='merge',
        unique_key='item_line_id',
        partition_by={'field': 'dispensing_date', 'data_type': 'date', 'granularity': 'month'},
        cluster_by=['icb_code', 'bnf_chapter_code'],
        on_schema_change='append_new_columns'
    )
}}

-- Grain: one dispensed prescription line (double submissions removed).
-- Incremental: only lines whose updated_at moved past the fact's high-watermark (minus a small
-- look-back) are re-processed, then MERGEd on item_line_id: late arrivals are inserted into old
-- months' partitions and restated lines are updated in place.

with lines as (
    select *
    from {{ ref('int_prescription_items__priced') }}
    where not is_duplicate_submission
        {% if is_incremental() %}
            and updated_at >= (
                select timestamp_sub(max(existing.updated_at), interval {{ var('incremental_lookback_hours') }} hour)
                from {{ this }} as existing
            )
        {% endif %}
),

headers as (
    select
        prescription_id,
        patient_id,
        prescriber_id,
        practice_code,
        issue_date
    from {{ ref('stg_rx__prescriptions') }}
),

patients as (
    select
        patient_id,
        age_band,
        sex,
        imd_decile
    from {{ ref('stg_rx__patients') }}
),

practices as (
    select
        practice_code,
        icb_code,
        region_code
    from {{ ref('int_practices__enriched') }}
),

medicines as (
    select
        presentation_code,
        chapter_code,
        generic_available
    from {{ ref('int_medicines__bnf_hierarchy') }}
)

select
    l.item_line_id,
    l.prescription_id,
    l.dispensing_date,
    h.issue_date,
    l.presentation_code,
    m.chapter_code as bnf_chapter_code,
    h.practice_code,
    pr.icb_code,
    pr.region_code,
    h.prescriber_id,
    {{ dbt_utils.generate_surrogate_key(['pt.age_band', 'pt.sex', 'pt.imd_decile']) }} as patient_band_key,

    -- measures
    case when l.is_credit then -l.items else l.items end as items,
    l.quantity,
    l.net_ingredient_cost_filled as net_ingredient_cost,
    l.actual_cost_filled as actual_cost,
    l.tariff_unit_cost,
    l.potential_generic_saving,

    -- flags
    l.is_generic,
    m.generic_available,
    l.is_credit,
    l.is_late_arrival,
    l.arrival_lag_days,
    l.is_restated,
    l.is_nic_imputed,
    l.is_actual_cost_imputed,
    l.is_quantity_missing,

    -- lineage
    l.created_at as source_created_at,
    l.updated_at,
    current_timestamp() as dbt_loaded_at
from lines as l
inner join headers as h on l.prescription_id = h.prescription_id
inner join patients as pt on h.patient_id = pt.patient_id
inner join practices as pr on h.practice_code = pr.practice_code
inner join medicines as m on l.presentation_code = m.presentation_code
