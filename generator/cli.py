"""CLI: python -m generator [--lines N] [--loader bcp|odbc] [--skip-load]"""

from __future__ import annotations

import argparse
import logging
import time
from dataclasses import replace
from pathlib import Path

import numpy as np
from faker import Faker

from . import config as cfg
from .db import REPO_ROOT, SqlServerSettings, create_schema
from .dimensions import build_medicines, build_organisations, build_patients
from .loader import load
from .transactions import build_transactions

log = logging.getLogger("generator")


def generate(settings: cfg.Settings) -> tuple[dict, dict]:
    rng = np.random.default_rng(settings.seed)
    Faker.seed(settings.seed)
    fake = Faker("en_GB")

    t0 = time.perf_counter()
    org = build_organisations(rng, fake, settings.volumes, settings.dq)
    med = build_medicines(rng)
    pts = build_patients(rng, org, settings.volumes, settings.dq)
    log.info("reference data built in %.1fs", time.perf_counter() - t0)

    t0 = time.perf_counter()
    tx = build_transactions(rng, org, med, pts, settings.volumes, settings.dq)
    log.info("transactions built in %.1fs: %s", time.perf_counter() - t0, tx.stats)

    tables = {
        "region": org.region, "icb": org.icb, "practice": org.practice,
        "prescriber_type": org.prescriber_type, "prescriber": org.prescriber,
        "bnf_chapter": med.bnf_chapter, "bnf_section": med.bnf_section,
        "bnf_paragraph": med.bnf_paragraph, "bnf_chemical": med.bnf_chemical,
        "medicine": med.medicine, "medicine_price_history": med.medicine_price_history,
        "patient": pts.patient, "prescription": tx.prescription, "prescription_item": tx.prescription_item,
    }
    return tables, tx.stats


def main(argv: list[str] | None = None) -> None:
    p = argparse.ArgumentParser(prog="python -m generator", description="Generate and load synthetic RxSource data.")
    p.add_argument("--seed", type=int, default=cfg.SEED)
    p.add_argument("--lines", type=int, default=cfg.Volumes.target_lines, help="target prescription lines")
    p.add_argument("--patients", type=int, default=cfg.Volumes.patients)
    p.add_argument("--loader", choices=["auto", "bcp", "odbc"], default="auto")
    p.add_argument("--work-dir", type=Path, default=REPO_ROOT / "data" / "generated", help="where bcp files go")
    p.add_argument("--skip-load", action="store_true", help="generate only (no database changes)")
    p.add_argument("-v", "--verbose", action="store_true")
    args = p.parse_args(argv)

    logging.basicConfig(level=logging.DEBUG if args.verbose else logging.INFO,
                        format="%(asctime)s %(levelname)-5s %(name)s: %(message)s", datefmt="%H:%M:%S")

    volumes = replace(cfg.Volumes(), target_lines=args.lines, patients=args.patients)
    settings = cfg.Settings(seed=args.seed, volumes=volumes)
    tables, _ = generate(settings)
    for name, df in tables.items():
        log.info("%-24s %10s rows", name, f"{len(df):,}")
    if args.skip_load:
        return

    sql = SqlServerSettings()
    t0 = time.perf_counter()
    log.info("recreating database %s on %s", sql.database, sql.server)
    create_schema(sql)
    load(sql, tables, args.work_dir, args.loader)
    log.info("load finished in %.1fs. Next: python -m generator.check", time.perf_counter() - t0)
