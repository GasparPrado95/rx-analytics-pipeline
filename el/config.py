"""Load and validate the YAML pipeline configuration."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal

import yaml

DEFAULT_CONFIG = Path(__file__).with_name("config.yaml")
MODES = ("full", "incremental")
BACKENDS = ("sqlalchemy", "pyarrow", "pandas", "connectorx")


class ConfigError(ValueError):
    pass


@dataclass(frozen=True)
class TableConfig:
    name: str
    mode: Literal["full", "incremental"]
    primary_key: tuple[str, ...]
    cursor: str | None = None

    @property
    def write_disposition(self) -> str:
        return "merge" if self.mode == "incremental" else "replace"


@dataclass(frozen=True)
class RetryConfig:
    attempts: int = 3
    initial_wait_seconds: float = 10
    max_wait_seconds: float = 120


@dataclass(frozen=True)
class PipelineConfig:
    name: str
    dataset: str
    source_schema: str
    tables: tuple[TableConfig, ...]
    backend: str = "pyarrow"
    chunk_size: int = 100_000
    loader_file_format: str = "parquet"
    lag_seconds: float = 300
    retry: RetryConfig = field(default_factory=RetryConfig)

    def select(self, names: list[str] | None) -> tuple[TableConfig, ...]:
        """Tables to run, in config order. Unknown names are an error, not silently skipped."""
        if not names:
            return self.tables
        known = {t.name for t in self.tables}
        unknown = sorted(set(names) - known)
        if unknown:
            raise ConfigError(f"unknown table(s): {', '.join(unknown)}. Known: {', '.join(sorted(known))}")
        return tuple(t for t in self.tables if t.name in names)


def _table(raw: dict, index: int) -> TableConfig:
    where = f"tables[{index}]"
    if not isinstance(raw, dict) or "name" not in raw:
        raise ConfigError(f"{where}: each table needs a 'name'")
    name = raw["name"]
    mode = raw.get("mode", "full")
    if mode not in MODES:
        raise ConfigError(f"{where} ({name}): mode must be one of {MODES}, got {mode!r}")
    pk = raw.get("primary_key")
    if not pk:
        raise ConfigError(f"{where} ({name}): primary_key is required")
    pk = (pk,) if isinstance(pk, str) else tuple(pk)
    cursor = raw.get("cursor")
    if mode == "incremental" and not cursor:
        raise ConfigError(f"{where} ({name}): incremental tables need a 'cursor' column")
    if mode == "full" and cursor:
        raise ConfigError(f"{where} ({name}): 'cursor' only applies to incremental tables")
    extra = set(raw) - {"name", "mode", "primary_key", "cursor"}
    if extra:
        raise ConfigError(f"{where} ({name}): unknown keys {sorted(extra)}")
    return TableConfig(name=name, mode=mode, primary_key=pk, cursor=cursor)


def parse_config(raw: dict) -> PipelineConfig:
    if not isinstance(raw, dict) or "pipeline" not in raw or "tables" not in raw:
        raise ConfigError("config needs top-level 'pipeline' and 'tables' sections")
    p = raw["pipeline"]
    for key in ("name", "dataset", "source_schema"):
        if not p.get(key):
            raise ConfigError(f"pipeline.{key} is required")
    if p.get("backend", "pyarrow") not in BACKENDS:
        raise ConfigError(f"pipeline.backend must be one of {BACKENDS}")

    tables = tuple(_table(t, i) for i, t in enumerate(raw["tables"] or []))
    if not tables:
        raise ConfigError("at least one table is required")
    names = [t.name for t in tables]
    dupes = sorted({n for n in names if names.count(n) > 1})
    if dupes:
        raise ConfigError(f"duplicate table names: {dupes}")

    r = raw.get("retry") or {}
    retry = RetryConfig(
        attempts=int(r.get("attempts", 3)),
        initial_wait_seconds=float(r.get("initial_wait_seconds", 10)),
        max_wait_seconds=float(r.get("max_wait_seconds", 120)),
    )
    if float(p.get("lag_seconds", 300)) < 0:
        raise ConfigError("pipeline.lag_seconds must be >= 0")
    if retry.attempts < 1:
        raise ConfigError("retry.attempts must be >= 1")

    return PipelineConfig(
        name=p["name"], dataset=p["dataset"], source_schema=p["source_schema"], tables=tables,
        backend=p.get("backend", "pyarrow"), chunk_size=int(p.get("chunk_size", 100_000)),
        loader_file_format=p.get("loader_file_format", "parquet"),
        lag_seconds=float(p.get("lag_seconds", 300)), retry=retry,
    )


def load_config(path: Path = DEFAULT_CONFIG) -> PipelineConfig:
    with open(path, encoding="utf-8") as f:
        return parse_config(yaml.safe_load(f))
