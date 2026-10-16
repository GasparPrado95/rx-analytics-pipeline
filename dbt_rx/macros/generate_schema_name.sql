{#-
    prod: use the layer's dataset name as-is (stg_rx, int_rx, marts_rx, snapshots_rx).
    any other target (e.g. ci): prefix with the target dataset (ci_rx_stg_rx, ...) so CI runs
    never touch production datasets.
-#}
{% macro generate_schema_name(custom_schema_name, node) -%}
    {%- if custom_schema_name is none -%}
        {{ target.schema }}
    {%- elif target.name == 'prod' -%}
        {{ custom_schema_name | trim }}
    {%- else -%}
        {{ target.schema }}_{{ custom_schema_name | trim }}
    {%- endif -%}
{%- endmacro %}
