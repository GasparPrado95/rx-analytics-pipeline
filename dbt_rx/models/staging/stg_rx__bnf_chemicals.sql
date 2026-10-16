select
    chemical_code,
    trim(chemical_name) as chemical_name,
    paragraph_code
from {{ source('rx', 'bnf_chemical') }}
