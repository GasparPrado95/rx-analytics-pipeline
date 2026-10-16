from datetime import UTC, datetime

import pytest

from el import run as cli
from el.pipeline import RunResult


def test_parse_args_tables_and_flags():
    args = cli.parse_args(["--full-refresh", "--tables", "medicine, prescription_item,"])
    assert args.full_refresh
    assert args.tables == ["medicine", "prescription_item"]
    assert cli.parse_args([]).tables is None


def test_unknown_table_exits_with_config_error(tmp_path):
    assert cli.main(["--tables", "not_a_table", "--log-dir", str(tmp_path)]) == 2


@pytest.fixture
def fake_run(monkeypatch):
    calls = {}

    def run(cfg, tables, full_refresh=False):
        calls.update(tables=[t.name for t in tables], full_refresh=full_refresh)
        now = datetime.now(UTC)
        return RunResult(run_id="r", started_at=now, finished_at=now, status="success",
                         rows={t.name: 1 for t in tables})

    monkeypatch.setattr("el.pipeline.run", run)
    return calls


def test_main_passes_selection_and_refresh(fake_run, tmp_path):
    assert cli.main(["--tables", "region,icb", "--full-refresh", "--log-dir", str(tmp_path)]) == 0
    assert fake_run == {"tables": ["region", "icb"], "full_refresh": True}
    assert list(tmp_path.glob("el_*.log")), "a log file is written per run"


def test_main_returns_1_on_failure(monkeypatch, tmp_path):
    def boom(*a, **k):
        raise RuntimeError("bigquery down")

    monkeypatch.setattr("el.pipeline.run", boom)
    assert cli.main(["--tables", "region", "--log-dir", str(tmp_path)]) == 1
