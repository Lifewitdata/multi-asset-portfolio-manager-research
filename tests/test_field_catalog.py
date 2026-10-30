import re
import pandas as pd
import pytest
from multi_asset.config import ROOT, MACRO, ASSETS
from multi_asset.data import monthly_prices
from multi_asset.forecast import features, forecast

CATALOG = pd.read_csv(ROOT/"docs/field_catalog.csv", keep_default_na=False)
STATUSES = {"validated_input", "unit_tested", "reconciled", "traced", "documented_only"}
REQUIRED = ["dataset", "field", "type", "units", "source", "formula", "null_rule", "owner", "verification_status"]


def schema_columns():
    script = (ROOT/"sql/01_schema.sql").read_text(encoding="utf-8")
    tables = {}
    for name, body in re.findall(r"CREATE TABLE research\.\[(\w+)\] \((.*?)\n\);", script, flags=re.S):
        tables[name] = re.findall(r"^\s*\[(\w+)\]", body, flags=re.M)
    return tables


def test_every_sql_column_catalogued():
    tables = schema_columns()
    assert len(tables) == 12
    for table, columns in tables.items():
        documented = set(CATALOG[CATALOG.sql_table == table].field)
        assert set(columns) == documented, table


def test_csv_only_outputs_catalogued(daily_prices):
    frame = features(daily_prices)
    predictions, _ = forecast(daily_prices, minimum_train=len(frame)-3)
    expected = {"monthly_prices.csv": ["date", *monthly_prices(daily_prices).columns],
                "monthly_macro.csv": ["date", *MACRO],
                "volatility_predictions.csv": list(predictions.columns),
                "raw/prices.csv": list(daily_prices.columns)}
    for dataset, columns in expected.items():
        assert set(CATALOG[CATALOG.dataset == dataset].field) == set(columns), dataset
    assert set(ASSETS) <= set(CATALOG[CATALOG.dataset == "monthly_returns.csv"].field)


def test_required_attributes_and_status_vocabulary():
    assert not CATALOG.duplicated(["dataset", "field"]).any()
    for column in REQUIRED:
        assert (CATALOG[column].str.strip() != "").all(), column
    for row in CATALOG.itertuples():
        statuses = set(row.verification_status.split(";"))
        assert statuses <= STATUSES, row.field
        assert ("documented_only" in statuses) == (row.evidence == ""), (row.dataset, row.field)


@pytest.mark.parametrize("reference", sorted({r.strip() for e in CATALOG.evidence for r in e.split(";") if r.strip()}))
def test_evidence_references_exist(reference):
    path, _, name = reference.partition("::")
    target = ROOT/path
    assert target.exists(), reference
    if name:
        assert re.search(rf"^\s*def {re.escape(name)}\(", target.read_text(encoding="utf-8"), flags=re.M), reference
