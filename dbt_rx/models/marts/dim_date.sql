-- Contiguous calendar (Power BI date table) with NHS financial year (April-March) and season.
with spine as (
    {{ dbt_utils.date_spine(
        datepart='day',
        start_date="cast('" ~ var('date_spine_start') ~ "' as date)",
        end_date="cast('" ~ var('date_spine_end') ~ "' as date)"
    ) }}
),

days as (
    select cast(date_day as date) as date_day from spine
)

select
    date_day,
    extract(year from date_day) as year,
    extract(quarter from date_day) as quarter,
    extract(month from date_day) as month,
    format_date('%B', date_day) as month_name,
    format_date('%b', date_day) as month_short,
    format_date('%Y-%m', date_day) as year_month,
    date_trunc(date_day, month) as month_start,
    date_trunc(date_day, isoweek) as week_start,
    extract(isoweek from date_day) as iso_week,
    format_date('%A', date_day) as day_name,
    extract(dayofweek from date_day) in (1, 7) as is_weekend,
    -- NHS financial year runs April to March, e.g. 2024/25
    case
        when extract(month from date_day) >= 4
            then concat(
                    cast(extract(year from date_day) as string), '/',
                    format_date('%y', date_add(date_day, interval 1 year))
                )
        else concat(cast(extract(year from date_day) - 1 as string), '/', format_date('%y', date_day))
    end as nhs_financial_year,
    div(mod(extract(month from date_day) + 8, 12), 3) + 1 as nhs_financial_quarter,
    case
        when extract(month from date_day) in (12, 1, 2) then 'Winter'
        when extract(month from date_day) in (3, 4, 5) then 'Spring'
        when extract(month from date_day) in (6, 7, 8) then 'Summer'
        else 'Autumn'
    end as season
from days
