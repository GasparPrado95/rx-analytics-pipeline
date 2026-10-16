-- One row per data-quality check: how many rows were affected and how the pipeline handled them.
with lines as (
    select
        count(*) as total,
        countif(is_duplicate_submission) as duplicate_submission,
        countif(is_late_arrival) as late_arrival,
        countif(is_restated) as restated,
        countif(is_credit) as credit,
        countif(is_nic_imputed) as nic_imputed,
        countif(is_actual_cost_imputed) as actual_cost_imputed,
        countif(is_quantity_missing) as quantity_missing,
        countif(tariff_unit_cost is null) as no_tariff_price
    from {{ ref('int_prescription_items__priced') }}
),

patients as (
    select
        count(*) as total,
        countif(is_sex_code_nonstandard) as sex_nonstandard,
        countif(imd_decile is null) as imd_missing
    from {{ ref('stg_rx__patients') }}
),

practices as (
    select
        count(*) as total,
        countif(postcode_district is null) as postcode_missing,
        countif(is_rural_urban_nonstandard) as rural_urban_nonstandard
    from {{ ref('stg_rx__practices') }}
),

checks as (
    select c.*
    from lines
    cross join patients as pt
    cross join practices as pr
    cross join unnest([
        struct(
            'Duplicate submissions' as check_name, 'Prescription lines' as entity,
            lines.duplicate_submission as affected_rows, lines.total as total_rows,
            'Removed from the fact (earliest arrival kept)' as handling
        ),
        struct(
            'Late-arriving lines', 'Prescription lines', lines.late_arrival, lines.total,
            'Loaded via the updated_at watermark and merged into their dispensing month'
        ),
        struct(
            'Restated lines', 'Prescription lines', lines.restated, lines.total,
            'Latest version merged on item_line_id'
        ),
        struct(
            'Credit lines (negative)', 'Prescription lines', lines.credit, lines.total,
            'Kept with negative items and cost; flagged is_credit'
        ),
        struct(
            'Missing net ingredient cost', 'Prescription lines', lines.nic_imputed, lines.total,
            'Imputed as quantity x tariff price at dispensing date; flagged'
        ),
        struct(
            'Missing actual cost', 'Prescription lines', lines.actual_cost_imputed, lines.total,
            'Imputed from net ingredient cost; flagged'
        ),
        struct(
            'Missing quantity', 'Prescription lines', lines.quantity_missing, lines.total,
            'Kept; excluded from quantity-based measures'
        ),
        struct(
            'No tariff price at dispensing date', 'Prescription lines', lines.no_tariff_price, lines.total,
            'Expected to be zero; covered by a test'
        ),
        struct(
            'Non-standard sex code', 'Patients', pt.sex_nonstandard, pt.total,
            'Upper-cased; anything other than F/M mapped to U'
        ),
        struct(
            'Missing deprivation decile', 'Patients', pt.imd_missing, pt.total,
            'Kept as an Unknown band'
        ),
        struct(
            'Missing postcode district', 'Practices', pr.postcode_missing, pr.total,
            'Kept; the practice cannot be placed on a map'
        ),
        struct(
            'Non-standard rural/urban value', 'Practices', pr.rural_urban_nonstandard, pr.total,
            'Trimmed and title-cased'
        )
    ]) as c
)

select
    check_name,
    entity,
    affected_rows,
    total_rows,
    round(safe_divide(affected_rows, total_rows), 6) as affected_share,
    handling,
    current_timestamp() as checked_at
from checks
