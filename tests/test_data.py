import json
import numpy as np
import pandas as pd
import pytest
from multi_asset.data import validate_prices, monthly_prices, parse_yahoo, load

def test_monthly_grid(daily_prices):
    m=monthly_prices(daily_prices)
    assert m.shape==(145,10)
    assert m.pct_change(fill_method=None).iloc[1:].shape==(144,10)

@pytest.mark.parametrize("bad",[0,-1,np.nan,np.inf])
def test_invalid_prices_rejected(daily_prices,bad):
    daily_prices.loc[0,"adjusted_close"]=bad
    with pytest.raises(ValueError):validate_prices(daily_prices)

def test_duplicate_keys(daily_prices):
    with pytest.raises(ValueError):validate_prices(pd.concat([daily_prices,daily_prices.iloc[:1]]))

def test_missing_ticker(daily_prices):
    with pytest.raises(ValueError):validate_prices(daily_prices[daily_prices.ticker!="SPY"])

def test_missing_month_fails(daily_prices):
    p=daily_prices[~((daily_prices.ticker=="SPY")&(daily_prices.date.dt.to_period("M")==pd.Period("2018-01")))]
    with pytest.raises(ValueError):monthly_prices(p)

def test_stale_month_fails(daily_prices):
    p=daily_prices[~((daily_prices.ticker=="SPY")&(daily_prices.date.between("2018-01-20","2018-01-31")))]
    with pytest.raises(ValueError):monthly_prices(p)

def test_missing_cache_never_simulates(tmp_path):
    with pytest.raises(FileNotFoundError,match="--download"):load(tmp_path)

def test_tampered_cache_rejected(tmp_path):
    raw=tmp_path/"data/raw";raw.mkdir(parents=True)
    (raw/"prices.csv").write_text("bad")
    (raw/"manifest.json").write_text(json.dumps([{"file":"prices.csv","sha256":"incorrect"}]))
    with pytest.raises(ValueError,match="checksum"):load(tmp_path)

def test_provider_error():
    with pytest.raises(ValueError,match="Yahoo error"):
        parse_yahoo(json.dumps({"chart":{"error":"Unavailable"}}),"SPY")

def freeze(prices, ticker, start, end):
    p=prices.copy()
    mask=(p.ticker==ticker)&p.date.between(start,end)
    p.loc[mask,"adjusted_close"]=p.loc[mask,"adjusted_close"].iloc[0]
    return p

def test_frozen_price_rejected(daily_prices):
    # Rows keep arriving and the last observation is on time, so the month-end gap check passes.
    p=freeze(daily_prices,"MINT","2025-11-14","2025-11-28")
    with pytest.raises(ValueError,match="stale feed: MINT"):monthly_prices(p)

def test_short_repeat_allowed(daily_prices):
    validate_prices(freeze(daily_prices,"MINT","2025-11-14","2025-11-21"))

def test_cash_override(daily_prices):
    validate_prices(freeze(daily_prices,"BIL","2016-08-03","2016-08-17"))
    with pytest.raises(ValueError,match="stale feed: BIL"):
        validate_prices(freeze(daily_prices,"BIL","2016-08-01","2016-08-31"))
