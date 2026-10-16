select
    paragraph_code,
    trim(paragraph_name) as paragraph_name,
    section_code
from {{ source('rx', 'bnf_paragraph') }}
