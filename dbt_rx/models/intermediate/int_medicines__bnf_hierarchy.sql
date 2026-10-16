-- Presentation -> chemical -> paragraph -> section -> chapter, plus the generic equivalent's name.
with medicines as (
    select * from {{ ref('stg_rx__medicines') }}
),

-- Does any generic presentation exist for the chemical substance?
chemical_has_generic as (
    select
        chemical_code,
        logical_or(is_generic) as generic_available
    from medicines
    group by chemical_code
)

select
    m.presentation_code,
    m.presentation_name,
    m.is_generic,
    m.brand_name,
    m.generic_equivalent_code,
    g.presentation_name as generic_equivalent_name,
    -- A branded line counts as "generic available" only if it has a generic equivalent presentation.
    case when m.is_generic then true else m.generic_equivalent_code is not null end as generic_available,
    chg.generic_available as chemical_has_generic,
    m.form,
    m.strength,
    m.unit_of_measure,
    m.pack_quantity,
    m.current_unit_cost,
    c.chemical_code,
    c.chemical_name,
    p.paragraph_code,
    p.paragraph_name,
    s.section_code,
    s.section_name,
    ch.chapter_code,
    ch.chapter_name
from medicines as m
inner join {{ ref('stg_rx__bnf_chemicals') }} as c on m.chemical_code = c.chemical_code
inner join {{ ref('stg_rx__bnf_paragraphs') }} as p on c.paragraph_code = p.paragraph_code
inner join {{ ref('stg_rx__bnf_sections') }} as s on p.section_code = s.section_code
inner join {{ ref('stg_rx__bnf_chapters') }} as ch on s.chapter_code = ch.chapter_code
inner join chemical_has_generic as chg on m.chemical_code = chg.chemical_code
left join medicines as g on m.generic_equivalent_code = g.presentation_code
