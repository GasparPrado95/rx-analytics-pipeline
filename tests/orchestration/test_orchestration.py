from datetime import datetime
from pathlib import Path

import pytest

from orchestration import run as orch
from orchestration.run import StepResult


def test_summarise_run_results_counts_and_failures():
    results = {"results": [
        {"unique_id": "model.a", "status": "success"},
        {"unique_id": "test.b", "status": "pass"},
        {"unique_id": "test.c", "status": "fail", "message": "Got 3 results, configured to fail if != 0\nmore"},
        {"unique_id": "model.d", "status": "error", "message": None},
        {"unique_id": "model.e", "status": "skipped"},
    ]}
    counts, failures = orch.summarise_run_results(results)
    assert counts == {"success": 1, "pass": 1, "fail": 1, "error": 1, "skipped": 1}
    assert failures == ["test.c: fail Got 3 results, configured to fail if != 0", "model.d: error"]


def test_summarise_freshness_reports_stale_sources_with_age():
    sources = {"results": [
        {"unique_id": "source.rx.item", "status": "pass"},
        {"unique_id": "source.rx.log", "status": "warn", "max_loaded_at_time_ago_in_s": 3 * 86400},
        {"unique_id": "source.rx.hdr", "status": "error", "max_loaded_at_time_ago_in_s": 7200},
    ]}
    counts, problems = orch.summarise_freshness(sources)
    assert counts == {"pass": 1, "warn": 1, "error": 1}
    assert problems == ["source.rx.log: warn (72.0h old)", "source.rx.hdr: error (2.0h old)"]


@pytest.mark.parametrize("counts, rc, expected", [
    ({"success": 3, "pass": 10}, 0, True),
    ({"pass": 2, "warn": 1}, 0, True),       # warnings do not fail the run
    ({"pass": 2, "fail": 1}, 1, False),
    ({"success": 3}, 2, False),              # a crash fails even with clean counts
    ({"error": 1}, 0, False),
])
def test_is_success(counts, rc, expected):
    assert orch.is_success(counts, rc) is expected


def test_report_lists_steps_and_problems():
    steps = [
        StepResult("extract & load (dlt)", "success", 70, {"rows_loaded": 10}),
        StepResult("dbt build", "failed", 120, {"counts": {"fail": 1}}, ["test.x: fail"]),
    ]
    md = orch.render_markdown(datetime(2026, 10, 16, 6, 0), steps, Path("logs/p.log"))
    assert md.startswith("# Pipeline run 2026-10-16 06:00:00: FAILED")
    assert "| dbt build | failed | 120s |" in md
    assert "- **dbt build**: test.x: fail" in md


@pytest.fixture
def fake_steps(monkeypatch):
    calls = []

    def make(name, status="success"):
        def step(*args, **kwargs):
            calls.append(name)
            return StepResult(name, status)
        return step

    monkeypatch.setattr(orch, "step_simulate", make("simulate"))
    monkeypatch.setattr(orch, "step_el", make("el"))
    monkeypatch.setattr(orch, "step_dbt", lambda name, *a, **k: (calls.append(name), StepResult(name, "success"))[1])
    return calls, make


def test_main_runs_steps_in_order_and_writes_report(fake_steps, tmp_path):
    calls, _ = fake_steps
    assert orch.main(["--simulate", "--log-dir", str(tmp_path)]) == 0
    assert calls == ["simulate", "el", "dbt build", "dbt source freshness"]
    run_dir = next(tmp_path.glob("pipeline_*"))
    assert (run_dir / "report.md").exists() and (run_dir / "report.json").exists()


def test_main_stops_after_failed_el(fake_steps, monkeypatch, tmp_path):
    calls, make = fake_steps
    monkeypatch.setattr(orch, "step_el", make("el", "failed"))
    assert orch.main(["--log-dir", str(tmp_path)]) == 1
    assert calls == ["el"], "dbt must not run on top of a failed load"


def test_main_skips_are_reported(fake_steps, tmp_path):
    calls, _ = fake_steps
    assert orch.main(["--skip-el", "--skip-dbt", "--log-dir", str(tmp_path)]) == 0
    assert calls == []
    report = next(tmp_path.glob("pipeline_*/report.md")).read_text(encoding="utf-8")
    assert "| extract & load (dlt) | skipped |" in report
