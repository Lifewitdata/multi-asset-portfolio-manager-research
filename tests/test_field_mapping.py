"""The recorded review of the AI-drafted field mapping must agree with the catalog."""
import importlib.util
from pathlib import Path
import pytest

from multi_asset.config import ROOT

spec = importlib.util.spec_from_file_location("check_field_mapping", ROOT / "scripts/check_field_mapping.py")
checker = importlib.util.module_from_spec(spec)
spec.loader.exec_module(checker)


@pytest.fixture(scope="module")
def result():
    return checker.check()


def test_review_matches_catalog(result):
    rows, problems = result
    assert problems == []


def test_verdict_counts(result):
    rows, _ = result
    counts = {v: sum(1 for r in rows if r["verdict"] == v) for v in checker.ALLOWED_VERDICTS}
    assert counts == {"accepted": 3, "corrected": 6, "unknown_field": 1}


def test_draft_is_ten_proposals_with_ids(result):
    rows, _ = result
    assert len(rows) == 10
    assert [r["id"] for r in rows] == [f"P-{i:02d}" for i in range(1, 11)]


def test_corrected_rows_name_the_contradicted_attribute(result):
    rows, _ = result
    for row in rows:
        if row["verdict"] == "accepted":
            assert row["mismatched"] == []
        elif row["verdict"] == "unknown_field":
            assert row["mismatched"] == ["field is not in the catalog"]
        else:
            assert row["mismatched"], row
            assert all(attribute in checker.ATTRIBUTES for attribute in row["mismatched"])


def test_adjusted_close_draft_is_rejected_for_the_price_basis(result):
    """Unadjusted close is the one mapping mistake that would change every return silently."""
    row = next(r for r in result[0] if r["id"] == "P-03")
    assert row["verdict"] == "corrected"
    assert {"source", "units", "null_rule"} <= set(row["mismatched"])


def test_yield_units_are_not_read_as_decimals(result):
    row = next(r for r in result[0] if r["id"] == "P-06")
    assert "units" in row["mismatched"]


def test_units_compare_verbatim_not_as_substrings():
    catalog_units = "USD per share, split/distribution adjusted"
    assert checker.agrees("USD per share", catalog_units, exact=True) is False
    assert checker.agrees(catalog_units, catalog_units, exact=True) is True
    assert checker.agrees("USD per share", catalog_units, exact=False) is True


def test_fragment_source_paths_pass_and_absent_paths_fail():
    authoritative = "Yahoo Finance chart API v8 chart.result[0].timestamp"
    assert checker.agrees("chart.result[0].timestamp", authoritative, exact=False) is True
    assert checker.agrees("chart.result[0].meta.symbol", authoritative, exact=False) is False


def test_blank_proposal_is_never_agreement():
    assert checker.agrees("", "Never null", exact=False) is False


def test_unknown_field_has_no_attributes_to_compare():
    verdict, mismatches = checker.evaluate({"dataset": "raw/prices.csv", "field": "nope"}, None)
    assert (verdict, mismatches) == ("unknown_field", [])


def test_missing_correction_text_is_a_problem():
    proposal = {"id": "P-99", "dataset": "raw/prices.csv", "field": "date", "reviewed_as": "corrected",
                "source": "not the real source", "formula": "", "units": "wrong", "null_rule": "",
                "correction": "", "catalog_reference": ""}
    references = checker.catalog_rows()
    verdict, _ = checker.evaluate(proposal, references[("raw/prices.csv", "date")])
    assert verdict == "corrected"
    assert not proposal["correction"].strip()


def test_normalise_maps_typographic_dashes_and_spaces():
    assert checker.normalise("  std(r \u2013 comparator,\u00a0 ddof=1)\n") == "std(r - comparator, ddof=1)"
