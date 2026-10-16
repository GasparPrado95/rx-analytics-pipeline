import copy

import pytest

from el.config import DEFAULT_CONFIG, ConfigError, load_config, parse_config

VALID = {
    "pipeline": {"name": "p", "dataset": "raw", "source_schema": "rx"},
    "tables": [
        {"name": "region", "mode": "full", "primary_key": "region_code"},
        {"name": "item", "mode": "incremental", "primary_key": ["id"], "cursor": "updated_at"},
    ],
}


def cfg_with(**changes):
    raw = copy.deepcopy(VALID)
    for path, value in changes.items():
        section, key = path.split("__")
        if section == "t0":
            raw["tables"][0][key] = value
        elif section == "t1":
            raw["tables"][1][key] = value
        else:
            raw[section][key] = value
    return raw


def test_repo_config_is_valid():
    cfg = load_config(DEFAULT_CONFIG)
    names = [t.name for t in cfg.tables]
    assert "prescription_item" in names
    item = next(t for t in cfg.tables if t.name == "prescription_item")
    assert item.mode == "incremental"
    assert item.cursor == "updated_at"
    assert item.write_disposition == "merge"


def test_defaults_and_write_dispositions():
    cfg = parse_config(VALID)
    assert cfg.backend == "pyarrow"
    assert cfg.retry.attempts == 3
    assert cfg.lag_seconds == 300
    region, item = cfg.tables
    assert region.write_disposition == "replace"
    assert region.primary_key == ("region_code",)  # string normalised to tuple
    assert item.write_disposition == "merge"


@pytest.mark.parametrize(
    "changes, message",
    [
        ({"t0__mode": "append"}, "mode must be one of"),
        ({"t1__cursor": None}, "need a 'cursor'"),
        ({"t0__cursor": "updated_at"}, "only applies to incremental"),
        ({"t0__primary_key": None}, "primary_key is required"),
        ({"t0__colour": "red"}, "unknown keys"),
        ({"pipeline__dataset": ""}, "pipeline.dataset is required"),
        ({"pipeline__backend": "odbc"}, "pipeline.backend"),
        ({"pipeline__lag_seconds": -1}, "lag_seconds"),
    ],
)
def test_invalid_configs_are_rejected(changes, message):
    with pytest.raises(ConfigError, match=message):
        parse_config(cfg_with(**changes))


def test_duplicate_table_names_rejected():
    raw = copy.deepcopy(VALID)
    raw["tables"].append(dict(raw["tables"][0]))
    with pytest.raises(ConfigError, match="duplicate"):
        parse_config(raw)


def test_missing_sections_rejected():
    with pytest.raises(ConfigError, match="top-level"):
        parse_config({"pipeline": VALID["pipeline"]})


def test_select_keeps_config_order_and_rejects_unknown():
    cfg = parse_config(VALID)
    assert [t.name for t in cfg.select(["item", "region"])] == ["region", "item"]
    assert cfg.select(None) == cfg.tables
    with pytest.raises(ConfigError, match="unknown table"):
        cfg.select(["region", "nope"])
