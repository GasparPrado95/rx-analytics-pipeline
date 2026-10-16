"""Local orchestration: EL -> dbt build -> dbt source freshness -> report.

    python -m orchestration.run                  # the scheduled daily run
    python -m orchestration.run --simulate       # first write a new source batch (demo)
    python -m orchestration.run --full-refresh   # rebuild raw tables and the incremental fact
    python -m orchestration.run --skip-el        # dbt only

Each step runs as a subprocess so one step's logging or crash cannot corrupt another.
Results are read from machine-readable files (EL summary JSON, dbt run_results.json and
sources.json), and a Markdown + JSON report is written to logs/. Exit code 1 if any step failed.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path

from dotenv import dotenv_values

REPO_ROOT = Path(__file__).resolve().parents[1]
DBT_DIR = REPO_ROOT / "dbt_rx"


@dataclass
class StepResult:
    name: str
    status: str  # success / failed / skipped
    duration_seconds: float = 0.0
    details: dict = field(default_factory=dict)
    failures: list[str] = field(default_factory=list)


# --------------------------------------------------------------------------
# Parsing tool outputs
# --------------------------------------------------------------------------


def summarise_run_results(run_results: dict) -> tuple[dict, list[str]]:
    """dbt target/run_results.json -> counts by status, plus failure messages."""
    counts: dict[str, int] = {}
    failures = []
    for r in run_results.get("results", []):
        status = r.get("status", "unknown")
        counts[status] = counts.get(status, 0) + 1
        if status in {"error", "fail", "runtime error"}:
            msg = (r.get("message") or "").splitlines()[0][:200] if r.get("message") else ""
            failures.append(f"{r.get('unique_id')}: {status} {msg}".strip())
    return counts, failures


def summarise_freshness(sources: dict) -> tuple[dict, list[str]]:
    """dbt target/sources.json -> counts by freshness status, plus stale/erroring sources."""
    counts: dict[str, int] = {}
    problems = []
    for r in sources.get("results", []):
        status = r.get("status", "unknown")
        counts[status] = counts.get(status, 0) + 1
        if status in {"error", "runtime error", "warn"}:
            age = r.get("max_loaded_at_time_ago_in_s")
            age_txt = f" ({age / 3600:.1f}h old)" if isinstance(age, int | float) else ""
            problems.append(f"{r.get('unique_id')}: {status}{age_txt}")
    return counts, problems


def is_success(counts: dict, returncode: int) -> bool:
    if returncode != 0:
        return False
    bad = {"error", "fail", "runtime error"}
    return not any(counts.get(s, 0) for s in bad)


# --------------------------------------------------------------------------
# Steps
# --------------------------------------------------------------------------


def _env() -> dict[str, str]:
    """Process env plus the repo's .env (dbt reads project/key settings via env_var())."""
    env = dict(os.environ)
    env.update({k: v for k, v in dotenv_values(REPO_ROOT / ".env").items() if v is not None})
    env.setdefault("PYTHONIOENCODING", "utf-8")
    return env


def _dbt_executable() -> str:
    scripts = Path(sys.executable).parent
    for name in ("dbt.exe", "dbt"):
        if (scripts / name).exists():
            return str(scripts / name)
    return "dbt"


def _run(cmd: list[str], cwd: Path, log_file: Path) -> tuple[int, float]:
    t0 = time.perf_counter()
    with open(log_file, "a", encoding="utf-8") as log:
        log.write(f"\n$ {' '.join(cmd)}\n")
        log.flush()
        proc = subprocess.run(cmd, cwd=cwd, env=_env(), stdout=log, stderr=subprocess.STDOUT, text=True)
    return proc.returncode, time.perf_counter() - t0


def step_simulate(log_file: Path) -> StepResult:
    rc, secs = _run([sys.executable, "-m", "generator.simulate"], REPO_ROOT, log_file)
    return StepResult("simulate source batch", "success" if rc == 0 else "failed", secs)


def step_el(log_file: Path, run_dir: Path, full_refresh: bool) -> StepResult:
    summary_path = run_dir / "el_summary.json"
    cmd = [sys.executable, "-m", "el.run", "--summary-json", str(summary_path)]
    if full_refresh:
        cmd.append("--full-refresh")
    rc, secs = _run(cmd, REPO_ROOT, log_file)
    summary = json.loads(summary_path.read_text(encoding="utf-8")) if summary_path.exists() else {}
    rows = summary.get("rows", {})
    details = {
        "run_id": summary.get("run_id"),
        "rows_loaded": sum(rows.values()),
        "incremental_rows": {k: v for k, v in rows.items() if k in summary.get("watermarks", {})},
    }
    failures = [summary["error"]] if summary.get("error") else ([] if rc == 0 else [f"exit code {rc}"])
    return StepResult("extract & load (dlt)", "success" if rc == 0 else "failed", secs, details, failures)


def step_dbt(name: str, args: list[str], artifact: str, summarise, log_file: Path, target: str) -> StepResult:
    artifact_path = DBT_DIR / "target" / artifact
    artifact_path.unlink(missing_ok=True)  # never report a previous run's results
    rc, secs = _run([_dbt_executable(), *args, "--target", target], DBT_DIR, log_file)
    if not artifact_path.exists():
        return StepResult(name, "failed", secs, failures=[f"dbt exited {rc} without writing {artifact}"])
    counts, failures = summarise(json.loads(artifact_path.read_text(encoding="utf-8")))
    ok = is_success(counts, rc)
    return StepResult(name, "success" if ok else "failed", secs, {"counts": counts}, failures)


# --------------------------------------------------------------------------
# Report
# --------------------------------------------------------------------------


def render_markdown(started: datetime, steps: list[StepResult], log_file: Path) -> str:
    overall = "SUCCESS" if all(s.status in {"success", "skipped"} for s in steps) else "FAILED"
    lines = [
        f"# Pipeline run {started:%Y-%m-%d %H:%M:%S}: {overall}",
        "",
        "| Step | Status | Duration | Details |",
        "|---|---|---:|---|",
    ]
    for s in steps:
        detail = ", ".join(f"{k}={v}" for k, v in s.details.items() if v not in (None, {}, []))
        lines.append(f"| {s.name} | {s.status} | {s.duration_seconds:.0f}s | {detail} |")
    problems = [f"- **{s.name}**: {f}" for s in steps for f in s.failures]
    if problems:
        lines += ["", "## Problems", *problems]
    lines += ["", f"Full log: `{log_file}`"]
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="python -m orchestration.run", description=__doc__.splitlines()[0])
    p.add_argument("--simulate", action="store_true", help="write a new batch into the source first (demo)")
    p.add_argument("--full-refresh", action="store_true", help="full-refresh EL and dbt incremental models")
    p.add_argument("--skip-el", action="store_true")
    p.add_argument("--skip-dbt", action="store_true")
    p.add_argument("--target", default="prod", help="dbt target (default: prod)")
    p.add_argument("--log-dir", type=Path, default=REPO_ROOT / "logs")
    args = p.parse_args(argv)

    started = datetime.now()
    run_dir = args.log_dir / f"pipeline_{started:%Y%m%d_%H%M%S}"
    run_dir.mkdir(parents=True, exist_ok=True)
    log_file = run_dir / "pipeline.log"
    steps: list[StepResult] = []

    def record(step: StepResult) -> bool:
        steps.append(step)
        print(f"[{datetime.now():%H:%M:%S}] {step.name}: {step.status} ({step.duration_seconds:.0f}s)", flush=True)
        return step.status == "success"

    ok = True
    if args.simulate:
        ok = record(step_simulate(log_file))
    if args.skip_el:
        steps.append(StepResult("extract & load (dlt)", "skipped"))
    elif ok:
        ok = record(step_el(log_file, run_dir, args.full_refresh))
    if args.skip_dbt:
        steps.append(StepResult("dbt build", "skipped"))
    elif ok:
        build_args = ["build"] + (["--full-refresh"] if args.full_refresh else [])
        ok = record(step_dbt("dbt build", build_args, "run_results.json", summarise_run_results, log_file, args.target))
        # Freshness runs even if the build failed tests: it is a separate signal worth reporting.
        fresh = step_dbt("dbt source freshness", ["source", "freshness"], "sources.json",
                         summarise_freshness, log_file, args.target)
        ok = record(fresh) and ok

    report = render_markdown(started, steps, log_file)
    (run_dir / "report.md").write_text(report, encoding="utf-8")
    (run_dir / "report.json").write_text(
        json.dumps({"started": started.isoformat(), "success": ok, "steps": [asdict(s) for s in steps]}, indent=2),
        encoding="utf-8",
    )
    print("\n" + report)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
