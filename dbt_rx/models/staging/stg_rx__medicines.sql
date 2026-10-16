select
    presentation_code,
    trim(presentation_name) as presentation_name,
    chemical_code,
    is_generic,
    brand_name,
    generic_equivalent_code,
    form,
    strength,
    unit_of_measure,
    pack_quantity,
    unit_cost as current_unit_cost,
    updated_at
from {{ source('rx', 'medicine') }}
