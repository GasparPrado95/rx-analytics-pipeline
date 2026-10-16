import importlib.util
from pathlib import Path

import pytest

spec = importlib.util.spec_from_file_location(
    "drop_ci_datasets", Path(__file__).resolve().parents[2] / "scripts" / "drop_ci_datasets.py"
)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

DATASETS = ["raw_rx", "marts_rx", "ci_pr7", "ci_pr7_stg_rx", "ci_pr7_marts_rx", "ci_pr70_marts_rx", "ci_pr8_stg_rx"]


def test_selects_only_this_runs_datasets():
    assert mod.select_datasets(DATASETS, "ci_pr7") == ["ci_pr7", "ci_pr7_marts_rx", "ci_pr7_stg_rx"]


@pytest.mark.parametrize("prefix", ["", "ci_", "raw", "marts_rx", "c"])
def test_refuses_unsafe_prefixes(prefix):
    with pytest.raises(ValueError, match="refusing"):
        mod.select_datasets(DATASETS, prefix)
