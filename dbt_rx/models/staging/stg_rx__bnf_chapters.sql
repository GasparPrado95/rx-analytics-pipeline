select chapter_code, trim(chapter_name) as chapter_name
from {{ source('rx', 'bnf_chapter') }}
