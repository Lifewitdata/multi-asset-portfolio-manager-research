"""Deterministic synthetic unit fixtures only; never a production-data fallback."""
import numpy as np
import pandas as pd
import pytest
from multi_asset.config import ASSETS

@pytest.fixture
def returns():
    rng=np.random.default_rng(42)
    frame=pd.DataFrame(rng.normal(.004,.025,(60,len(ASSETS))),index=pd.date_range("2014-01-31",periods=60,freq="ME"),columns=list(ASSETS))
    frame["BIL"]=rng.normal(.001,.0001,len(frame))
    return frame

@pytest.fixture
def daily_prices():
    rng=np.random.default_rng(7)
    dates=pd.bdate_range("2013-12-01","2025-12-31")
    frames=[]
    for t in ASSETS:
        prices=100*np.exp(np.cumsum(rng.normal(.0001,.005,len(dates))))
        frames.append(pd.DataFrame({"date":dates,"ticker":t,"adjusted_close":prices}))
    return pd.concat(frames,ignore_index=True)
