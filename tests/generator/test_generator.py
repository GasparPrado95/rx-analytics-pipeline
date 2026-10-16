from dataclasses import replace

import numpy as np
import pandas as pd
import pytest

from generator import config as cfg
from generator.cli import generate
from generator.dimensions import _allocate
from generator.transactions import _cumulative_by_group, _pick_within_group


def test_allocate_hits_total_and_floor():
    alloc = _allocate(400, np.array([3.0, 0.1, 1.7, 2.4]), minimum=3)
    assert alloc.sum() == 400
    assert alloc.min() >= 3
    assert alloc[0] > alloc[2] > alloc[1]


def test_pick_within_group_stays_in_group_and_respects_weights():
    rng = np.random.default_rng(0)
    groups = np.array([0, 0, 0, 1, 1, 2])
    weights = np.array([1.0, 0.0, 3.0, 1.0, 1.0, 5.0])
    picker = _cumulative_by_group(groups, weights, 3)
    asked = rng.integers(0, 3, 20_000)
    picked = _pick_within_group(rng, *picker, asked)
    assert (groups[picked] == asked).all()
    assert not (picked == 1).any(), "zero-weight rows are never picked"
    in_g0 = picked[asked == 0]
    assert 0.70 < (in_g0 == 2).mean() < 0.80  # weight 3 vs 1


@pytest.fixture(scope="module")
def small():
    tables, stats = generate(cfg.Settings(volumes=replace(cfg.Volumes(), target_lines=30_000)))
    return tables, stats


def test_generation_is_reproducible(small):
    again, _ = generate(cfg.Settings(volumes=replace(cfg.Volumes(), target_lines=30_000)))
    for name, df in small[0].items():
        pd.testing.assert_frame_equal(df, again[name], obj=name)


def test_line_volume_close_to_target(small):
    _, stats = small
    assert abs(stats["lines"] - 30_000) / 30_000 < 0.05


def test_referential_integrity_in_memory(small):
    t, _ = small
    assert t["prescription_item"]["prescription_id"].isin(t["prescription"]["prescription_id"]).all()
    assert t["prescription_item"]["presentation_code"].isin(t["medicine"]["presentation_code"]).all()
    rx = t["prescription"].merge(t["prescriber"][["prescriber_id", "practice_code"]], on="prescriber_id")
    assert (rx["practice_code_x"] == rx["practice_code_y"]).all()


def test_price_history_has_one_open_row_matching_current_price(small):
    t, _ = small
    h, m = t["medicine_price_history"], t["medicine"]
    open_rows = h[h["effective_to"].isna()]
    assert open_rows["presentation_code"].is_unique
    assert len(open_rows) == len(m)
    merged = m.merge(open_rows, on="presentation_code", suffixes=("", "_h"))
    assert np.allclose(merged["unit_cost"], merged["unit_cost_h"])


def test_timestamps_never_exceed_source_snapshot(small):
    t, _ = small
    item = t["prescription_item"]
    limit = np.datetime64(cfg.AS_OF) + np.timedelta64(1, "D")
    assert (item["created_at"].to_numpy() < limit).all()
    assert (item["updated_at"] >= item["created_at"]).all()
