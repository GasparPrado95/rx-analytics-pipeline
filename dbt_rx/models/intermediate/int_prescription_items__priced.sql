-- Prices each line at its dispensing date and fills cost gaps (always flagged, never silently).
--   net_ingredient_cost missing -> quantity x tariff price in force at dispensing  (is_nic_imputed);
--                                  else actual cost / var('actual_cost_to_nic_ratio'),
--                                  else items x pack quantity x tariff price
--   actual_cost missing         -> NIC x var('actual_cost_to_nic_ratio')            (is_actual_cost_imputed)
--   potential_generic_saving    -> branded lines with a generic equivalent: (brand - generic price) x quantity
with items as (
    select * from {{ ref('int_prescription_items__flagged') }}
),

prices as (
    select * from {{ ref('stg_rx__medicine_price_history') }}
),

medicines as (
    select presentation_code, is_generic, generic_equivalent_code, pack_quantity
    from {{ ref('stg_rx__medicines') }}
),

priced as (
    select
        i.*,
        m.is_generic,
        m.generic_equivalent_code,
        m.pack_quantity,
        p.unit_cost as tariff_unit_cost,
        gp.unit_cost as generic_tariff_unit_cost
    from items as i
    inner join medicines as m
        on m.presentation_code = i.presentation_code
    left join prices as p
        on p.presentation_code = i.presentation_code
        and i.dispensing_date between p.effective_from and p.effective_to
    left join prices as gp
        on gp.presentation_code = m.generic_equivalent_code
        and i.dispensing_date between gp.effective_from and gp.effective_to
),

filled as (
    select
        *,
        coalesce(
            net_ingredient_cost,
            round(quantity * tariff_unit_cost, 2),
            round(actual_cost / {{ var('actual_cost_to_nic_ratio') }}, 2),
            round(items * pack_quantity * tariff_unit_cost, 2)
        ) as net_ingredient_cost_filled,
        net_ingredient_cost is null as is_nic_imputed,
        quantity is null as is_quantity_missing
    from priced
)

select
    * except (net_ingredient_cost_filled, pack_quantity),
    net_ingredient_cost_filled,
    coalesce(
        actual_cost,
        round(net_ingredient_cost_filled * {{ var('actual_cost_to_nic_ratio') }}, 2)
    ) as actual_cost_filled,
    actual_cost is null and net_ingredient_cost_filled is not null as is_actual_cost_imputed,
    case
        when not is_generic and generic_equivalent_code is not null and quantity > 0
            then round(greatest(tariff_unit_cost - generic_tariff_unit_cost, 0) * quantity, 2)
        else 0
    end as potential_generic_saving
from filled
