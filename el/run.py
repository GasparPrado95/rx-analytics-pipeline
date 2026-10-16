"""CLI entry point.

    python -m el.run                         # incremental run, all tables
    python -m el.run --full-refresh          # drop raw tables + watermarks, reload everything
    python -m el.run --tables prescription_item,medicine
"""

from __future__ import annotations

import argparse
import logging
import sys
import warnings
from datetime import datetime
from pathlib import Path

from .config import DEFAULT_CONFIG, ConfigError, load_config
from .connections import REPO_ROOT, SettingsError

log = logging.getLogger("el")


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(prog="python -m el.run", description="Extract RxSource (SQL Server) into BigQuery.")
    p.add_argument("--full-refresh", action="store_true",
                   help="drop the selected raw tables and their watermarks, then reload from scratch")
    p.add_argument("--tables", type=lambda s: [t.strip() for t in s.split(",") if t.strip()],
                   help="comma-separated subset of tables (default: all in config)")
    p.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    p.add_argument("--log-dir", type=Path, default=REPO_ROOT / "logs")
    p.add_argument("-v", "--verbose", action="store_true")
    return p.parse_args(argv)


def setup_logging(log_dir: Path, verbose: bool) -> Path:
    log_dir.mkdir(parents=True, exist_ok=True)
    log_file = log_dir / f"el_{datetime.now():%Y%m%d_%H%M%S}.log"
    fmt = logging.Formatter("%(asctime)s %(levelname)-7s %(name)s: %(message)s", "%Y-%m-%d %H:%M:%S")
    console = logging.StreamHandler(sys.stdout)
    console.setFormatter(fmt)
    console.setLevel(logging.DEBUG if verbose else logging.INFO)
    file = logging.FileHandler(log_file, encoding="utf-8")
    file.setFormatter(fmt)
    file.setLevel(logging.DEBUG)
    root = logging.getLogger()
    root.setLevel(logging.DEBUG)
    root.handlers[:] = [console, file]
    # Optional fast-read client; this pipeline only writes via load jobs.
    warnings.filterwarnings("ignore", message="Cannot create BigQuery Storage client")
    for noisy in ("urllib3", "google", "sqlalchemy", "dlt", "filelock"):
        logging.getLogger(noisy).setLevel(logging.WARNING)
    return log_file


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    log_file = setup_logging(args.log_dir, args.verbose)
    try:
        cfg = load_config(args.config)
        tables = cfg.select(args.tables)
    except ConfigError as exc:
        log.error("config error: %s", exc)
        return 2

    from .pipeline import run  # deferred: dlt import is slow and not needed for --help / config errors

    try:
        result = run(cfg, tables, full_refresh=args.full_refresh)
    except SettingsError as exc:
        log.error("settings error: %s", exc)
        return 2
    except Exception:
        log.exception("EL run failed (details in %s)", log_file)
        return 1

    secs = (result.finished_at - result.started_at).total_seconds()
    log.info("run %s succeeded in %.0fs", result.run_id, secs)
    for t in tables:
        wm = result.watermark_after.get(t.name)
        log.info("  %-24s %10s rows%s", t.name, f"{result.rows.get(t.name, 0):,}", f"  watermark {wm}" if wm else "")
    log.info("log file: %s", log_file)
    return 0


if __name__ == "__main__":
    sys.exit(main())
