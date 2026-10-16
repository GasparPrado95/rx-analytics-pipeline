-- Each medicine's price versions must tile time with no gaps or overlaps, and end with one open
-- version. Otherwise some dispensing dates would get no price (or two).
with ordered as (
    select
        presentation_code,
        effective_from,
        effective_to,
        lead(effective_from) over (partition by presentation_code order by effective_from) as next_from
    from {{ ref('stg_rx__medicine_price_history') }}
)

select *
from ordered
where (next_from is not null and date_add(effective_to, interval 1 day) != next_from)
   or (next_from is null and effective_to != date '9999-12-31')
