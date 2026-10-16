[← Back to README](../README.md)

# Phase 4: Orchestration & CI

### Local orchestration (`orchestration/`, `scripts/`)

One entry point runs the whole pipeline and reports on it:

```powershell
python -m orchestration.run                 # EL -> dbt build -> dbt source freshness -> report
python -m orchestration.run --simulate      # write a new source batch first (demo)
python -m orchestration.run --full-refresh  # rebuild raw tables and the incremental fact
.\scripts\run_pipeline.ps1                  # the same, via the venv (what Task Scheduler calls)
```

- **Isolated steps:** each step runs as a subprocess, so one step's logging or crash cannot
  corrupt another. dbt does not run on top of a failed load.
- **Report from machine-readable files:** the EL `--summary-json`, plus dbt's
  `run_results.json` and `sources.json`. No console scraping.
- **Report location:** each run writes `logs/pipeline_<timestamp>/report.md` and `report.json`,
  plus the full `pipeline.log`.
- **Exit code:** 0 on success, 1 if any step failed. Task Scheduler shows it as *Last Run Result*.

Example report:

| Step | Status | Duration | Details |
|---|---|---:|---|
| extract & load (dlt) | success | 71s | rows_loaded=56599, incremental_rows={'prescription': 12, 'prescription_item': 2520} |
| dbt build | success | 142s | counts={'success': 29, 'pass': 140} |
| dbt source freshness | success | 12s | counts={'pass': 2} |

#### Scheduling with Windows Task Scheduler

```powershell
.\scripts\register_scheduled_task.ps1              # daily at 06:00 as the current user
.\scripts\register_scheduled_task.ps1 -At '07:30'
Start-ScheduledTask -TaskName 'rx-analytics-pipeline'                   # run now
(Get-ScheduledTaskInfo -TaskName 'rx-analytics-pipeline').LastTaskResult # 0 = success
Unregister-ScheduledTask -TaskName 'rx-analytics-pipeline' -Confirm:$false
```

The task runs as your user, only while you're logged on. That's what Windows authentication to
SQL Server needs, and it means no password is stored. It catches up after missed runs, retries
twice at 15-minute intervals, and never overlaps itself.

To do it by hand in the Task Scheduler UI instead:
1. *Create Task*.
2. Set *Run only when user is logged on*.
3. Add a *Daily* trigger.
4. Add an action: program `powershell.exe`, arguments
   `-NoProfile -ExecutionPolicy Bypass -File "<repo>\scripts\run_pipeline.ps1"`, start in `<repo>`.

### GitHub Actions

| Workflow | Trigger | What it does |
|---|---|---|
| [`ci.yml`](../.github/workflows/ci.yml) | pull request to `main` | **Python job:** `ruff`, `pytest`. **dbt job:** `sqlfluff` (dbt templater, BigQuery dialect), `dbt build --target ci` into isolated `ci_pr<N>_*` datasets, source freshness (informational), artifacts uploaded, CI datasets dropped (`if: always()`) |
| [`docs.yml`](../.github/workflows/docs.yml) | push to `main` | `dbt docs generate --static` → GitHub Pages: **https://gasparprado95.github.io/rx-analytics-pipeline/** |

**Repository settings used by the workflows:**

| Name | Kind | Value |
|---|---|---|
| `GCP_SA_KEY` | **secret** | Full JSON key of the CI service account (`rx-ci`, roles BigQuery Data Editor + BigQuery Job User) |
| `GCP_PROJECT_ID` | variable | `rx-analytics-pipeline` |

To set the secret from PowerShell:
`Get-Content "<path-to-ci-key>.json" -Raw | gh secret set GCP_SA_KEY --repo GasparPrado95/rx-analytics-pipeline`.
Or in the UI: *Settings → Secrets and variables → Actions → New repository secret*.

**Why a separate CI service account?** A leaked CI key can be revoked without breaking the local
pipeline, and BigQuery audit logs show which jobs came from CI.

### Trade-off: CI cannot reach the local SQL Server

GitHub-hosted runners cannot connect to a SQL Server on a home machine, and opening it to the
internet would be the wrong fix. So:

- **CI covers dbt and Python.** dbt builds every model, the snapshot and all 169 tests from the
  production `raw_rx` dataset (read-only), into throwaway `ci_pr<N>_*` datasets. Python logic
  is covered by unit tests.
- **The EL step is verified locally**, by the orchestrator and the reconciliation checks in
  Phase 2. It's not end-to-end in CI.
- **Ways to close the gap:**
  - a self-hosted runner on the same machine;
  - a cloud-hosted source (e.g. Azure SQL or Cloud SQL) with private networking;
  - a containerised SQL Server in CI, seeded by the generator at a small `--lines` value.

Each CI run scans ~2 GB and briefly stores ~0.6 GB, well within the free tier. Slim CI
(`dbt build --select state:modified+ --defer`) would cut that further as the project grows.

### Lint configuration

- **ruff:** `pyproject.toml`.
- **sqlfluff:** `dbt_rx/.sqlfluff`. BigQuery dialect, dbt templater, lower-case keywords,
  explicit aliases, 120-character lines. Three rules are excluded, each with a reason in the file.
