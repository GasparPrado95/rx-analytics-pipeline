-- A line cannot be dispensed before its prescription was issued.
select item_line_id, issue_date, dispensing_date
from {{ ref('fct_prescription_items') }}
where dispensing_date < issue_date
