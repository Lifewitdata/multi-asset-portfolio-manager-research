"""Real SQL Server, explicitly synthetic rows; never vendor data or historical evidence.

Set MULTI_ASSET_SQLSERVER_TEST_URL to a disposable empty database. Normal unit runs skip.
"""
import os
import re
from datetime import date
import pandas as pd
import pytest
from sqlalchemy import text
from multi_asset import database
from multi_asset.reconcile import export

pytestmark = pytest.mark.skipif(not os.getenv('MULTI_ASSET_SQLSERVER_TEST_URL'), reason='Disposable SQL Server not configured')


def test_transactional_load_roundtrip_and_rollback(monkeypatch, tmp_path):
    monkeypatch.setenv('MULTI_ASSET_SQLSERVER_URL', os.environ['MULTI_ASSET_SQLSERVER_TEST_URL'])
    # Build one deliberately synthetic, schema-complete row per table. Schema constraints
    # and independent values below exercise types, nullable metrics, FKs and dates.
    schema = (database.ROOT / 'sql/01_schema.sql').read_text()
    frames = {}
    for name in database.KEYS:
        block = schema.split(f'CREATE TABLE research.[{name}] (', 1)[1].split('CONSTRAINT', 1)[0]
        row = {}
        for col, dtype, nullable in re.findall(r'\[(\w+)\] (NVARCHAR\(128\)|FLOAT|INT|DATE) (NOT NULL|NULL)', block):
            row[col] = (None if nullable == 'NULL' else
                        date(2024, 1, 1) if col == 'training_end' else
                        date(2024, 2, 1) if dtype == 'DATE' else
                        'SYNTHETIC' if dtype.startswith('NVARCHAR') else
                        12 if dtype == 'INT' else 0.125)
        frames[name] = pd.DataFrame([row])
    monkeypatch.setattr(database, 'prepared_frames', lambda: frames)
    monkeypatch.setattr(database, 'export', lambda s, m: export(s, m, folder=tmp_path))
    database.load_sqlserver()
    database.load_sqlserver()  # idempotent MERGE, not duplicate append
    actual = database.read_dashboard(list(frames))
    for name in frames:
        assert len(actual[name]) == 1
    assert actual['daily_prices'].adjusted_close.item() == 0.125
    assert pd.isna(actual['fund_metrics'].sharpe_cash_proxy.item())
    # Earlier table update must roll back when a later FK/check constraint rejects a row.
    frames['assets'].loc[0, 'name'] = 'MUST ROLL BACK'
    frames['daily_prices'].loc[0, 'adjusted_close'] = -1
    from sqlalchemy.exc import DBAPIError
    with pytest.raises(DBAPIError):
        database.load_sqlserver()
    after = database.read_dashboard(['assets', 'daily_prices'])
    assert after['assets'].name.item() == 'SYNTHETIC'
    assert after['daily_prices'].adjusted_close.item() == 0.125
    db = database.engine()
    try:
        with db.connect() as conn:
            assert conn.execute(text("SELECT COUNT(*) FROM sys.tables WHERE name LIKE 'stage[_]%'" )).scalar_one() == 0
    finally:
        db.dispose()
