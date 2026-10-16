from datetime import UTC, datetime

import pytest
from dlt.common.destination.exceptions import DestinationTransientException

from el.config import RetryConfig, TableConfig, parse_config
from el.pipeline import (
    SOURCE_NAME,
    RunResult,
    incremental_for,
    is_transient,
    run_log_rows,
    run_with_retry,
    watermarks,
)

FULL = TableConfig("region", "full", ("region_code",))
INCR = TableConfig("prescription_item", "incremental", ("item_line_id",), "updated_at")
FAST_RETRY = RetryConfig(attempts=3, initial_wait_seconds=0, max_wait_seconds=0)


class OperationalError(Exception):
    """Same name as pyodbc's / SQLAlchemy's connection error."""


class PipelineStepFailed(Exception):
    """Mimics dlt: wraps the real error in `.exception`."""

    def __init__(self, inner):
        super().__init__("step failed")
        self.exception = inner


# ---------- transient error classification ----------

@pytest.mark.parametrize("exc", [
    OperationalError("login timeout"),
    ConnectionResetError("reset"),
    TimeoutError("slow"),
    DestinationTransientException("bq 503"),
    PipelineStepFailed(OperationalError("wrapped")),
])
def test_transient_errors(exc):
    assert is_transient(exc)


def test_transient_found_through_cause_chain():
    try:
        try:
            raise TimeoutError("socket")
        except TimeoutError as inner:
            raise RuntimeError("load failed") from inner
    except RuntimeError as outer:
        assert is_transient(outer)


@pytest.mark.parametrize("exc", [ValueError("bad config"), KeyError("col"), PipelineStepFailed(ValueError("schema"))])
def test_permanent_errors(exc):
    assert not is_transient(exc)


def test_cyclic_exception_chain_terminates():
    a, b = ValueError("a"), ValueError("b")
    a.__context__, b.__context__ = b, a
    assert not is_transient(a)


# ---------- retry ----------

def test_retry_recovers_from_transient_failures():
    calls = []

    def flaky():
        calls.append(1)
        if len(calls) < 3:
            raise TimeoutError("try again")
        return "ok"

    assert run_with_retry(flaky, FAST_RETRY, sleep=lambda _: None) == "ok"
    assert len(calls) == 3


def test_retry_gives_up_after_max_attempts():
    calls = []

    def always_down():
        calls.append(1)
        raise TimeoutError("down")

    with pytest.raises(TimeoutError):
        run_with_retry(always_down, FAST_RETRY, sleep=lambda _: None)
    assert len(calls) == 3


def test_permanent_errors_are_not_retried():
    calls = []

    def broken():
        calls.append(1)
        raise ValueError("bug")

    with pytest.raises(ValueError):
        run_with_retry(broken, FAST_RETRY, sleep=lambda _: None)
    assert len(calls) == 1


# ---------- incremental settings ----------

def test_incremental_only_for_tables_with_cursor():
    cfg = parse_config({
        "pipeline": {"name": "p", "dataset": "d", "source_schema": "rx", "lag_seconds": 120},
        "tables": [{"name": "t", "primary_key": "id"}],
    })
    assert incremental_for(FULL, cfg) is None
    inc = incremental_for(INCR, cfg)
    assert inc.cursor_path == "updated_at"
    assert inc.range_start == "closed"  # >= watermark: rows sharing the boundary timestamp are re-read
    assert inc.lag == 120
    assert inc.primary_key == ()  # no boundary dedup state: the merge makes re-reads idempotent


# ---------- reporting ----------

def test_watermarks_read_from_dlt_state():
    wm = datetime(2026, 4, 30, 23, 59, 59, tzinfo=UTC)
    state = {"sources": {SOURCE_NAME: {"resources": {
        "prescription_item": {"incremental": {"updated_at": {"last_value": wm}}},
    }}}}
    assert watermarks(state, [FULL, INCR]) == {"prescription_item": wm}


def test_watermarks_before_first_load():
    assert watermarks({}, [FULL, INCR]) == {"prescription_item": None}


def test_run_log_rows():
    started = datetime(2026, 10, 16, 3, 0, tzinfo=UTC)
    result = RunResult(
        run_id="r1", started_at=started, finished_at=started, status="success",
        rows={"prescription_item": 2520},
        watermark_before={"prescription_item": "2026-04-30T23:59:59+00:00"},
        watermark_after={"prescription_item": datetime(2026, 10, 16, 3, 47, 20)},  # naive -> UTC
    )
    rows = {r["table_name"]: r for r in run_log_rows(result, [FULL, INCR])}
    assert rows["region"]["rows_loaded"] == 0
    assert rows["region"]["watermark_after"] is None
    item = rows["prescription_item"]
    assert item["rows_loaded"] == 2520
    assert item["load_mode"] == "incremental"
    assert item["watermark_before"] == datetime(2026, 4, 30, 23, 59, 59, tzinfo=UTC)
    assert item["watermark_after"].tzinfo is UTC
    assert item["error_message"] is None


def test_run_log_truncates_errors():
    result = RunResult(run_id="r", started_at=datetime.now(UTC), status="failed", error="x" * 5000)
    (row,) = run_log_rows(result, [FULL])
    assert len(row["error_message"]) == 1000
