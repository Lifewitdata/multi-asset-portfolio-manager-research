import json
import sqlite3
from datetime import date
import numpy as np
import pandas as pd
import pytest
from multi_asset.reconcile import compare, reconcile, export


@pytest.fixture
def source():
    return pd.DataFrame({"date": [date(2025, 1, 31), date(2025, 1, 31), date(2025, 2, 28)],
                         "portfolio": ["A", "B", "A"], "net_return": [0.01, -0.02, 0.003],
                         "alpha": [0.1, np.nan, 0.2], "training_end": [date(2024, 12, 31)] * 3})


def issues(result):
    return sorted(zip(result[1].column, result[1].issue))


def test_identical_frames_pass(source):
    summary, mismatches = compare("t", source, source.copy(), ["date", "portfolio"])
    assert summary["status"] == "PASS" and mismatches.empty
    assert summary["cells_compared"] == 3 * 3 and summary["max_abs_diff"] == 0


def test_date_types_normalised(source):
    target = source.copy()
    target["date"] = pd.to_datetime(target.date)
    target["training_end"] = target.training_end.astype(str)
    assert compare("t", source, target, ["date", "portfolio"])[0]["status"] == "PASS"


def test_within_tolerance_passes_beyond_fails(source):
    target = source.copy()
    target.loc[0, "net_return"] += 1e-15
    assert compare("t", source, target, ["date", "portfolio"])[0]["status"] == "PASS"
    target.loc[0, "net_return"] += 1e-6
    summary, mismatches = compare("t", source, target, ["date", "portfolio"])
    assert issues((summary, mismatches)) == [("net_return", "value_diff")]
    assert mismatches.abs_diff.iloc[0] == pytest.approx(1e-6, rel=1e-3)
    assert json.loads(mismatches.key.iloc[0]) == {"date": "2025-01-31", "portfolio": "A"}


def test_one_part_per_billion_price_change_detected():
    source = pd.DataFrame({"ticker": ["MINT"], "adjusted_close": [50.123]})
    target = source.assign(adjusted_close=source.adjusted_close * 1.000000001)
    assert compare("t", source, target, ["ticker"])[0]["status"] == "FAIL"


def test_null_rules(source):
    target = source.copy()
    target["alpha"] = target.alpha.astype(object).where(target.alpha.notna(), None)
    assert compare("t", source, target, ["date", "portfolio"])[0]["status"] == "PASS"
    target.loc[0, "alpha"] = None
    assert issues(compare("t", source, target, ["date", "portfolio"])) == [("alpha", "null_mismatch")]


def test_missing_extra_rows_and_columns(source):
    target = pd.concat([source.iloc[1:], pd.DataFrame([{**source.iloc[0].to_dict(), "portfolio": "Z"}])])
    target = target.drop(columns="alpha").assign(extra=1)
    found = issues(compare("t", source, target, ["date", "portfolio"]))
    assert found == [("<row>", "missing_in_target"), ("<row>", "unexpected_in_target"),
                     ("alpha", "missing_column"), ("extra", "unexpected_column")]


def test_text_and_date_value_changes(source):
    target = source.copy()
    target.loc[2, "training_end"] = date(2025, 1, 31)
    assert issues(compare("t", source, target, ["date", "portfolio"])) == [("training_end", "value_diff")]


def test_duplicate_keys_refused(source):
    with pytest.raises(ValueError, match="duplicate"):
        compare("t", source, pd.concat([source, source.iloc[:1]]), ["date", "portfolio"])


def test_sqlite_roundtrip_and_export(source, tmp_path):
    con = sqlite3.connect(":memory:")
    source.to_sql("returns", con, index=False)
    summaries, mismatches = reconcile({"returns": source}, lambda n: pd.read_sql(f"SELECT * FROM {n}", con),
                                      {"returns": ["date", "portfolio"]})
    assert summaries[0]["status"] == "PASS"
    con.execute("UPDATE returns SET net_return = 0.5 WHERE portfolio = 'B'")
    summaries, mismatches = reconcile({"returns": source}, lambda n: pd.read_sql(f"SELECT * FROM {n}", con),
                                      {"returns": ["date", "portfolio"]})
    report = export(summaries, mismatches, tmp_path)
    assert report["status"] == "FAIL" and report["total_mismatches"] == 1
    exported = pd.read_csv(tmp_path/"mismatches.csv")
    assert exported.loc[0, "column"] == "net_return" and exported.loc[0, "target_value"] == 0.5
