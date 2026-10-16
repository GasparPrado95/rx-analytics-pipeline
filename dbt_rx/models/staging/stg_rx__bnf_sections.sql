select section_code, trim(section_name) as section_name, chapter_code
from {{ source('rx', 'bnf_section') }}
