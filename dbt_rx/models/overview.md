{% docs __overview__ %}

# rx-analytics-pipeline: dbt project

Transforms **synthetic** NHS England primary-care prescribing data (modelled on the public
English Prescribing Dataset) from the raw BigQuery copy of the `RxSource` SQL Server database
into a star schema for Power BI.

> All data is synthetic. No row describes a real patient, prescriber or practice.

## Layers

| Layer | Dataset | Materialisation | Purpose |
|---|---|---|---|
| sources | `raw_rx` | loaded by dlt | Untouched copy of the source, plus `el_run_log` |
| staging | `stg_rx` | views | 1:1 with sources: rename, cast, normalise codes, dedupe on primary key |
| intermediate | `int_rx` | views | Business rules: flag double submissions and late arrivals, price at dispensing date, impute and flag missing costs |
| marts | `marts_rx` | tables | Star schema (`fct_prescription_items` + dims) and aggregates |
| snapshots | `snapshots_rx` | snapshot | SCD2 history of medicine prices |

## Star schema

`fct_prescription_items` (one row per dispensed line, incremental, partitioned by month,
clustered by ICB and BNF chapter) joins to `dim_medicine`, `dim_practice`, `dim_prescriber`,
`dim_patient_band` and `dim_date`. The marts never expose a patient identifier: facts link to an
age band x sex x deprivation band.

## Data-quality handling

The source deliberately contains defects. See `mart_data_quality_checks` for counts and handling:
double submissions (removed), late arrivals (merged into their month), restatements (latest
version wins), missing costs (imputed and flagged), credit lines (kept as negatives), and
inconsistent codes (normalised).

{% enddocs %}
