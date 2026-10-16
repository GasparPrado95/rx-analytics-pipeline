"""Write tables to tab-separated files and bulk-load them into SQL Server.

Primary path: bcp in character mode with TABLOCK (minimally logged under SIMPLE
recovery). bcp skips foreign-key checks during the load, so afterwards every
table is re-validated with WITH CHECK CHECK CONSTRAINT ALL: constraints end up
*trusted*, which the optimizer relies on and the integrity checks verify.

Fallback path: pyodbc with fast_executemany (array binding), for machines
without the bcp utility.
"""

from __future__ import annotations

import logging
import re
import shutil
import subprocess
import time
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path

import numpy as np
import pandas as pd

from .db import SqlServerSettings, connect, create_indexes

log = logging.getLogger(__name__)

# Load order respects foreign keys (parents first).
LOAD_ORDER = [
    "region", "icb", "practice", "prescriber_type", "prescriber",
    "bnf_chapter", "bnf_section", "bnf_paragraph", "bnf_chemical",
    "medicine", "medicine_price_history", "patient",
    "prescription", "prescription_item",
]
IDENTITY_TABLES = {"prescription_item"}


def _prepare(df: pd.DataFrame) -> pd.DataFrame:
    """Make every column bcp-parseable: ISO dates/datetimes as text, booleans as 0/1.

    Numbers stay numeric so to_csv can format them in C (much faster than per-value
    Python formatting); NULLs become empty fields.
    """
    out = df.copy()
    for col in df.columns:
        s = df[col]
        if pd.api.types.is_datetime64_any_dtype(s):
            unit = "D" if col.endswith("_date") or col.startswith("effective_") else "s"
            arr = np.datetime_as_string(s.to_numpy().astype(f"datetime64[{unit}]"), unit=unit)
            out[col] = np.where(s.isna(), "", np.char.replace(arr, "T", " "))
        elif pd.api.types.is_bool_dtype(s):
            out[col] = s.astype(int)
        elif not pd.api.types.is_numeric_dtype(s):
            first = s.dropna().iloc[0] if s.notna().any() else None
            if isinstance(first, date):  # python date objects (e.g. price history)
                out[col] = s.map(lambda v: v.isoformat() if isinstance(v, date) else "")
            elif col.endswith("_at"):
                # bcp's char-mode datetime2 cast rejects the ISO 'T' separator
                out[col] = s.str.replace("T", " ", regex=False)
    return out


def _is_text(s: pd.Series) -> bool:
    return not pd.api.types.is_numeric_dtype(s) and not pd.api.types.is_bool_dtype(s)


def write_tsv(df: pd.DataFrame, path: Path) -> None:
    out = _prepare(df)
    text_cols = [c for c in out.columns if _is_text(out[c])]
    bad = [c for c in text_cols if out[c].astype(str).str.contains(r"[\t\n]", regex=True).any()]
    if bad:
        raise ValueError(f"{path.name}: tab/newline inside columns {bad}")
    # 4 decimals covers every DECIMAL column (values are pre-rounded to their scale).
    out.to_csv(path, sep="\t", header=False, index=False, lineterminator="\n", encoding="utf-8",
               na_rep="", float_format="%.4f")


def _check_columns(settings: SqlServerSettings, tables: dict[str, pd.DataFrame]) -> None:
    """Fail fast if a DataFrame's columns don't match the table's column order."""
    with connect(settings) as conn:
        cur = conn.cursor()
        for name, df in tables.items():
            cur.execute(
                "SELECT COLUMN_NAME FROM INFORMATION_SCHEMA.COLUMNS "
                "WHERE TABLE_SCHEMA='rx' AND TABLE_NAME=? ORDER BY ORDINAL_POSITION", name)
            db_cols = [r[0] for r in cur.fetchall()]
            if db_cols != list(df.columns):
                raise ValueError(f"rx.{name}: column mismatch\n  db: {db_cols}\n  df: {list(df.columns)}")


def bcp_available() -> bool:
    return shutil.which("bcp") is not None


def load_with_bcp(settings: SqlServerSettings, tables: dict[str, pd.DataFrame], work_dir: Path) -> dict[str, int]:
    work_dir.mkdir(parents=True, exist_ok=True)
    loaded = {}
    for name in LOAD_ORDER:
        df = tables[name]
        path = work_dir / f"{name}.tsv"
        t0 = time.perf_counter()
        write_tsv(df, path)
        cmd = [
            "bcp", f"rx.{name}", "in", str(path),
            "-S", settings.server, "-d", settings.database, "-T",
            "-c", "-C", "65001", "-t", "\\t", "-r", "0x0a",
            "-k",  # keep NULLs for empty fields
            "-b", "250000", "-h", "TABLOCK", "-m", "1",
            "-e", str(work_dir / f"{name}.bcp.err"),
        ]
        if settings.trust_cert:
            cmd.append("-u")
        if name in IDENTITY_TABLES:
            cmd.append("-E")  # keep the generator's ids
        res = subprocess.run(cmd, capture_output=True, text=True)
        match = re.search(r"(\d+) rows copied", res.stdout)
        if res.returncode != 0 or not match or int(match.group(1)) != len(df):
            raise RuntimeError(f"bcp failed for rx.{name} (rc={res.returncode}):\n{res.stdout}\n{res.stderr}")
        loaded[name] = int(match.group(1))
        log.info("bcp  rx.%-24s %10s rows  %6.1fs", name, f"{loaded[name]:,}", time.perf_counter() - t0)
    return loaded


# fast_executemany binds by the parameter's SQL type, so values must be native Python types.
_PARSERS = {
    "int": int, "bigint": int, "smallint": int, "tinyint": int, "bit": int,
    "decimal": lambda v: Decimal(f"{v:.4f}"), "date": date.fromisoformat, "datetime2": datetime.fromisoformat,
}


def _native(parser, value):
    if value is None or value is pd.NA or value == "" or (isinstance(value, float) and np.isnan(value)):
        return None
    return parser(value)


def load_with_odbc(settings: SqlServerSettings, tables: dict[str, pd.DataFrame], chunk: int = 50_000) -> dict[str, int]:
    loaded = {}
    with connect(settings) as conn:
        cur = conn.cursor()
        cur.fast_executemany = True
        for name in LOAD_ORDER:
            df = tables[name]
            t0 = time.perf_counter()
            cur.execute("SELECT DATA_TYPE FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_SCHEMA='rx' AND TABLE_NAME=? "
                        "ORDER BY ORDINAL_POSITION", name)
            parsers = [_PARSERS.get(r[0], str) for r in cur.fetchall()]
            prepared = _prepare(df)
            rows = [tuple(_native(f, v) for f, v in zip(parsers, r, strict=False))
                    for r in prepared.itertuples(index=False, name=None)]
            cols = ", ".join(df.columns)
            sql = f"INSERT INTO rx.{name} ({cols}) VALUES ({', '.join('?' * len(df.columns))})"
            if name in IDENTITY_TABLES:
                cur.execute(f"SET IDENTITY_INSERT rx.{name} ON")
            for i in range(0, len(rows), chunk):
                cur.executemany(sql, rows[i: i + chunk])
            if name in IDENTITY_TABLES:
                cur.execute(f"SET IDENTITY_INSERT rx.{name} OFF")
            conn.commit()
            loaded[name] = len(rows)
            log.info("odbc rx.%-24s %10s rows  %6.1fs", name, f"{len(rows):,}", time.perf_counter() - t0)
    return loaded


def finalise(settings: SqlServerSettings) -> None:
    """Build secondary indexes, re-validate all constraints (trusted again) and refresh statistics."""
    t0 = time.perf_counter()
    create_indexes(settings)
    log.info("secondary indexes built in %.1fs", time.perf_counter() - t0)
    with connect(settings, autocommit=True) as conn:
        cur = conn.cursor()
        for name in LOAD_ORDER:
            cur.execute(f"ALTER TABLE rx.{name} WITH CHECK CHECK CONSTRAINT ALL")
        cur.execute("DBCC CHECKIDENT ('rx.prescription_item', RESEED) WITH NO_INFOMSGS")
        cur.execute("EXEC sp_updatestats")
        while cur.nextset():
            pass


def load(
    settings: SqlServerSettings, tables: dict[str, pd.DataFrame], work_dir: Path, method: str = "auto"
) -> dict[str, int]:
    _check_columns(settings, tables)
    if method == "auto":
        method = "bcp" if bcp_available() else "odbc"
    log.info("loading with %s", method)
    loaded = load_with_bcp(settings, tables, work_dir) if method == "bcp" else load_with_odbc(settings, tables)
    finalise(settings)
    return loaded
