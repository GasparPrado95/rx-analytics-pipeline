"""Run the RxSource row-count / referential-integrity checks and fail on violations.

Usage: python -m generator.check [--expected-lines N]
Exit code 1 if any integrity check is non-zero or a row count is out of range.
"""

from __future__ import annotations

import argparse
import sys

from . import config as cfg
from .db import REPO_ROOT, SqlServerSettings, connect

CHECKS_SQL = REPO_ROOT / "sql_server" / "checks" / "integrity_checks.sql"


def expected_ranges(lines: int) -> dict[str, tuple[int, int]]:
    vol = cfg.Volumes()
    rx = lines / (1 + vol.lines_per_prescription_extra)
    return {
        "rx.region": (7, 7),
        "rx.icb": (42, 42),
        "rx.practice": (vol.practices, vol.practices),
        "rx.prescriber_type": (3, 3),
        "rx.prescriber": (vol.prescribers, vol.prescribers),
        "rx.bnf_chapter": (13, 13),
        "rx.bnf_section": (40, 80),
        "rx.bnf_paragraph": (60, 120),
        "rx.bnf_chemical": (120, 250),
        "rx.medicine": (500, 700),
        "rx.medicine_price_history": (500, 3000),
        "rx.patient": (vol.patients, vol.patients),
        "rx.prescription": (int(rx * 0.9), int(rx * 1.1)),
        "rx.prescription_item": (int(lines * 0.95), int(lines * 1.05)),
    }


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="python -m generator.check")
    p.add_argument("--expected-lines", type=int, default=cfg.Volumes.target_lines)
    args = p.parse_args(argv)

    with connect(SqlServerSettings()) as conn:
        cur = conn.cursor()
        sql = CHECKS_SQL.read_text(encoding="utf-8")
        cur.execute(sql)
        while cur.description is None and cur.nextset():  # skip USE / rowcount messages
            pass
        rows = cur.fetchall()

    ranges = expected_ranges(args.expected_lines)
    failures = 0
    current = None
    for category, name, value in rows:
        if category != current:
            current = category
            print(f"\n== {category} ==")
        status = ""
        if category == "rowcount" and name in ranges:
            lo, hi = ranges[name]
            ok = lo <= value <= hi
            status = "ok" if ok else f"FAIL (expected {lo:,}-{hi:,})"
        elif category == "integrity":
            ok = value == 0
            status = "ok" if ok else "FAIL"
        else:
            ok = True
        failures += not ok
        print(f"  {name:<58} {value:>12,}  {status}")

    print(f"\n{'PASSED' if failures == 0 else f'FAILED: {failures} check(s)'}")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
