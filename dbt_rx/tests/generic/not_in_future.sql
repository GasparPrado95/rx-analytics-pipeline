{#- Custom generic test: no date/timestamp in the column is later than now. -#}
{% test not_in_future(model, column_name) %}

select {{ column_name }}
from {{ model }}
where cast({{ column_name }} as timestamp) > current_timestamp()

{% endtest %}
