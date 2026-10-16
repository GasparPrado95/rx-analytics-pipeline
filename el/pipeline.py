"""dlt pipeline: SQL Server (sql_database source) -> BigQuery (raw dataset).

- Full tables use write_disposition=replace.
- Incremental tables use write_disposition=merge on their primary key, with a dlt
  `incremental` high-watermark on `updated_at`: closed range plus a lag window,
  made idempotent by the merge. dlt keeps the watermark in pipeline state,
  which it also stores in BigQuery (_dlt_pipeline_state), so a fresh machine resumes correctly.
- Every run appends one row per table to `el_run_log` for the pipeline-health dashboard.
"""

from __future__ import annotations

import logging
import uuid
from collections.abc import Callable, Iterable
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

import dlt
from dlt.common.destination.exceptions import DestinationTransientException
from dlt.destinations import bigquery
from dlt.sources.sql_database import sql_table
from sqlalchemy import create_engine
from tenacity import Retrying, retry_if_exception, stop_after_attempt, wait_exponential

from .config import PipelineConfig, RetryConfig, TableConfig
from .connections import DestinationSettings, SourceSettings

log = logging.getLogger(__name__)

SOURCE_NAME = "rx_source"
RUN_LOG_TABLE = "el_run_log"
# Explicit types: columns that are NULL on a run (e.g. error_message) still get created.
RUN_LOG_COLUMNS = {
    "run_id": {"data_type": "text", "nullable": False},
    "table_name": {"data_type": "text", "nullable": False},
    "load_mode": {"data_type": "text"},
    "status": {"data_type": "text", "nullable": False},
    "full_refresh": {"data_type": "bool"},
    "rows_loaded": {"data_type": "bigint"},
    "watermark_before": {"data_type": "timestamp"},
    "watermark_after": {"data_type": "timestamp"},
    "started_at": {"data_type": "timestamp"},
    "finished_at": {"data_type": "timestamp"},
    "error_message": {"data_type": "text"},
}

# --------------------------------------------------------------------------
# Retries: only for failures that are likely to succeed on a second attempt
# --------------------------------------------------------------------------

_TRANSIENT_NAMES = {
    # google.api_core.exceptions
    "ServiceUnavailable", "InternalServerError", "TooManyRequests", "GatewayTimeout", "DeadlineExceeded",
    "BadGateway", "RetryError",
    # network / driver
    "OperationalError", "ConnectionError", "ConnectionResetError", "TimeoutError", "ReadTimeout", "ConnectTimeout",
}


def _exception_chain(exc: BaseException) -> Iterable[BaseException]:
    """The exception plus everything it wraps (__cause__, __context__, dlt's .exception)."""
    seen: set[int] = set()
    stack = [exc]
    while stack:
        e = stack.pop()
        if e is None or id(e) in seen:
            continue
        seen.add(id(e))
        yield e
        stack.extend([e.__cause__, e.__context__, getattr(e, "exception", None)])


def is_transient(exc: BaseException) -> bool:
    for e in _exception_chain(exc):
        if isinstance(e, DestinationTransientException | ConnectionError | TimeoutError):
            return True
        if type(e).__name__ in _TRANSIENT_NAMES:
            return True
    return False


def run_with_retry(fn: Callable[[], Any], retry: RetryConfig, *, sleep: Callable[[float], None] | None = None) -> Any:
    """Call fn, retrying transient failures with exponential backoff. dlt resumes pending load packages."""
    kwargs = {"sleep": sleep} if sleep else {}
    retrying = Retrying(
        stop=stop_after_attempt(retry.attempts),
        wait=wait_exponential(multiplier=retry.initial_wait_seconds, max=retry.max_wait_seconds),
        retry=retry_if_exception(is_transient),
        reraise=True,
        before_sleep=lambda rs: log.warning(
            "attempt %d failed (%s); retrying in %.0fs",
            rs.attempt_number, rs.outcome.exception(), rs.next_action.sleep if rs.next_action else 0,
        ),
        **kwargs,
    )
    return retrying(fn)


# --------------------------------------------------------------------------
# Source definition
# --------------------------------------------------------------------------


def incremental_for(table: TableConfig, cfg: PipelineConfig):
    """High-watermark on the cursor: closed range (>=) plus a lag window, no boundary-row dedup state.

    A source batch commits many rows with the same updated_at. Instead of keeping a hash of every
    boundary row in pipeline state, rows at/behind the watermark are simply re-read and the merge
    on the primary key makes that idempotent.
    """
    if not table.cursor:
        return None
    return dlt.sources.incremental(
        table.cursor, primary_key=(), range_start="closed", lag=cfg.lag_seconds or None,
    )


def table_resource(engine, cfg: PipelineConfig, table: TableConfig):
    resource = sql_table(
        credentials=engine,
        table=table.name,
        schema=cfg.source_schema,
        backend=cfg.backend,
        chunk_size=cfg.chunk_size,
        reflection_level="full_with_precision",  # keep DECIMAL precision/scale and string lengths
        incremental=incremental_for(table, cfg),
        write_disposition=table.write_disposition,
        primary_key=list(table.primary_key),
    )
    return resource


def build_source(engine, cfg: PipelineConfig, tables: Iterable[TableConfig]):
    @dlt.source(name=SOURCE_NAME, max_table_nesting=0)
    def rx_source():
        return [table_resource(engine, cfg, t) for t in tables]

    return rx_source()


# --------------------------------------------------------------------------
# Reporting helpers
# --------------------------------------------------------------------------


def watermarks(state: dict, tables: Iterable[TableConfig]) -> dict[str, Any]:
    """Current high-watermark per incremental table from dlt pipeline state (None if never loaded)."""
    resources = state.get("sources", {}).get(SOURCE_NAME, {}).get("resources", {})
    out = {}
    for t in tables:
        if t.cursor:
            out[t.name] = resources.get(t.name, {}).get("incremental", {}).get(t.cursor, {}).get("last_value")
    return out


def _as_timestamp(value: Any) -> datetime | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=UTC)
    return datetime.fromisoformat(str(value))


@dataclass
class RunResult:
    run_id: str
    started_at: datetime
    finished_at: datetime | None = None
    status: str = "running"
    full_refresh: bool = False
    rows: dict[str, int] = field(default_factory=dict)
    watermark_before: dict[str, Any] = field(default_factory=dict)
    watermark_after: dict[str, Any] = field(default_factory=dict)
    error: str | None = None


def run_log_rows(result: RunResult, tables: Iterable[TableConfig]) -> list[dict]:
    """One el_run_log row per table for this run."""
    return [
        {
            "run_id": result.run_id,
            "table_name": t.name,
            "load_mode": t.mode,
            "status": result.status,
            "full_refresh": result.full_refresh,
            "rows_loaded": result.rows.get(t.name, 0),
            "watermark_before": _as_timestamp(result.watermark_before.get(t.name)),
            "watermark_after": _as_timestamp(result.watermark_after.get(t.name)),
            "started_at": result.started_at,
            "finished_at": result.finished_at,
            "error_message": (result.error or "")[:1000] or None,
        }
        for t in tables
    ]


# --------------------------------------------------------------------------
# Run
# --------------------------------------------------------------------------


def make_pipeline(cfg: PipelineConfig, dest: DestinationSettings):
    destination = bigquery(credentials=dest.credentials(), location=dest.location)
    return dlt.pipeline(pipeline_name=cfg.name, destination=destination, dataset_name=cfg.dataset)


def run(cfg: PipelineConfig, tables: tuple[TableConfig, ...], *, full_refresh: bool = False,
        source: SourceSettings | None = None, dest: DestinationSettings | None = None) -> RunResult:
    source = source or SourceSettings.from_env()
    dest = dest or DestinationSettings.from_env()
    result = RunResult(
        run_id=f"{datetime.now(UTC):%Y%m%dT%H%M%SZ}-{uuid.uuid4().hex[:6]}",
        started_at=datetime.now(UTC), full_refresh=full_refresh,
    )
    pipeline = make_pipeline(cfg, dest)
    engine = create_engine(source.sqlalchemy_url())
    log.info("run %s: %d table(s) %s -> bigquery %s.%s%s", result.run_id, len(tables), source.database,
             dest.project_id, cfg.dataset, " [FULL REFRESH]" if full_refresh else "")

    try:
        run_with_retry(pipeline.sync_destination, cfg.retry)  # restore state (watermarks) from BigQuery
        result.watermark_before = watermarks(pipeline.state, tables)
        for name, wm in result.watermark_before.items():
            log.info("  %-22s watermark before: %s", name, wm or "none (initial load)")

        load_info = run_with_retry(
            lambda: pipeline.run(
                build_source(engine, cfg, tables),
                loader_file_format=cfg.loader_file_format,
                refresh="drop_resources" if full_refresh else None,
            ),
            cfg.retry,
        )
        load_info.raise_on_failed_jobs()

        counts = pipeline.last_trace.last_normalize_info.row_counts if pipeline.last_trace else {}
        result.rows = {t.name: int(counts.get(t.name, 0)) for t in tables}
        result.watermark_after = watermarks(pipeline.state, tables)
        result.status = "success"
    except Exception as exc:
        result.status = "failed"
        result.error = f"{type(exc).__name__}: {exc}"
        raise
    finally:
        result.finished_at = datetime.now(UTC)
        engine.dispose()
        _write_run_log(pipeline, result, tables, cfg)

    return result


def _write_run_log(pipeline, result: RunResult, tables, cfg: PipelineConfig) -> None:
    """Best effort: a failure to log must not hide the real outcome of the run."""
    try:
        run_with_retry(
            lambda: pipeline.run(
                dlt.resource(run_log_rows(result, tables), name=RUN_LOG_TABLE, write_disposition="append",
                             columns=RUN_LOG_COLUMNS),
                schema=dlt.Schema("rx_el_meta"),
            ),
            cfg.retry,
        )
    except Exception:  # noqa: BLE001
        log.exception("could not write %s", RUN_LOG_TABLE)
