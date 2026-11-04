"""Regression checks for evidence overwrite and ambiguous reconciliation keys."""
import pandas as pd
import pytest
from multi_asset.reconcile import compare, export, MISMATCH_COLUMNS


def test_fault_export_preserves_clean_report(tmp_path):
    detail = pd.DataFrame(columns=MISMATCH_COLUMNS)
    export([], detail, folder=tmp_path, label='clean')
    before = (tmp_path / 'summary.json').read_bytes()
    export([], detail, folder=tmp_path, label='fault', prefix='injected_fault_')
    assert (tmp_path / 'summary.json').read_bytes() == before
    assert (tmp_path / 'injected_fault_summary.json').exists()
    assert (tmp_path / 'injected_fault_mismatches.csv').exists()


@pytest.mark.parametrize('target', [pd.DataFrame({'value': [1]}), pd.DataFrame({'id': [None], 'value': [1]})])
def test_invalid_keys_fail_clearly(target):
    with pytest.raises(ValueError, match='keys'):
        compare('sample', pd.DataFrame({'id': ['x'], 'value': [1]}), target, ['id'])


def test_public_fault_reports_do_not_contain_values():
    from multi_asset.config import ROOT
    for name in ['reports/incidents/stale_price_changed_cells.csv', 'reports/reconciliation/injected_fault_mismatches.csv']:
        columns = pd.read_csv(ROOT / name, nrows=0).columns
        assert not {'source_value', 'target_value', 'abs_diff', 'tolerance'} & set(columns)
