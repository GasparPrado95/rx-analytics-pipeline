-- One row per ICB per month: volumes, costs and rates per 1,000 registered (simulated panel) patients.
with facts as (
    select
        icb_code,
        date_trunc(dispensing_date, month) as month_start,
        items,
        net_ingredient_cost,
        actual_cost,
        is_generic,
        generic_available,
        potential_generic_saving,
        starts_with(presentation_code, '0501') as is_antibacterial
    from {{ ref('fct_prescription_items') }}
),

list_sizes as (
    select
        icb_code,
        any_value(icb_name) as icb_name,
        any_value(region_name) as region_name,
        sum(list_size) as list_size,
        sum(registered_patients) as registered_patients,
        count(*) as practices
    from {{ ref('dim_practice') }}
    group by icb_code
),

monthly as (
    select
        icb_code,
        month_start,
        sum(items) as total_items,
        sum(net_ingredient_cost) as total_net_ingredient_cost,
        sum(actual_cost) as total_actual_cost,
        sum(if(is_generic, items, 0)) as generic_items,
        sum(if(generic_available, items, 0)) as items_with_generic_available,
        sum(if(generic_available and is_generic, items, 0)) as generic_items_where_available,
        sum(if(is_antibacterial, items, 0)) as antibacterial_items,
        sum(potential_generic_saving) as potential_generic_saving
    from facts
    group by icb_code, month_start
)

select
    {{ dbt_utils.generate_surrogate_key(['m.icb_code', 'm.month_start']) }} as icb_month_key,
    m.icb_code,
    l.icb_name,
    l.region_name,
    m.month_start,
    l.practices,
    l.list_size,
    l.registered_patients,
    m.total_items,
    m.total_net_ingredient_cost,
    m.total_actual_cost,
    m.generic_items,
    m.antibacterial_items,
    m.potential_generic_saving,
    round(safe_divide(m.total_items, l.registered_patients) * 1000, 2) as items_per_1000_patients,
    round(safe_divide(m.antibacterial_items, l.registered_patients) * 1000, 3) as antibacterial_items_per_1000_patients,
    round(safe_divide(m.total_net_ingredient_cost, m.total_items), 4) as cost_per_item,
    -- EPD-style generic prescribing rate: share of items that were generic where a generic exists
    round(safe_divide(m.generic_items_where_available, m.items_with_generic_available), 4)
        as generic_prescribing_rate,
    round(safe_divide(m.generic_items, m.total_items), 4) as generic_items_share
from monthly as m
inner join list_sizes as l on l.icb_code = m.icb_code
