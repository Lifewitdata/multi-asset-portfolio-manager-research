import numpy as np
import pandas as pd
import pytest
from multi_asset.analytics import metrics,drawdown,evaluate_funds
from multi_asset.portfolio import optimize,policy_weights,step,backtest
from multi_asset.config import PROFILES,INVESTABLE
from multi_asset.forecast import features,forecast

def test_initial_loss_drawdown():
    r=pd.Series([-.20,.10])
    assert drawdown(r).iloc[0]==pytest.approx(-.2)
    assert drawdown(r).iloc[1]==pytest.approx(-.12)

def test_cagr_compounds(returns):
    r=returns.SPY
    m=metrics(r,returns.AGG,returns.BIL)
    assert m["cagr"]==pytest.approx((1+r).prod()**(12/len(r))-1)
    assert m["tracking_error"]==pytest.approx((r-returns.AGG).std()*np.sqrt(12))

def test_identical_benchmark_zero_te(returns):
    m=metrics(returns.SPY,returns.SPY,returns.BIL)
    assert m["tracking_error"]==0
    assert np.isnan(m["information_ratio"])
    # Exact fit: a p-value here would be rounding noise (it was 3.7e-7 for Growth Policy before the fix).
    assert np.isnan(m["alpha_pvalue_hac"])
    assert abs(m["alpha_annual"])<1e-12 and m["beta"]==pytest.approx(1)

def test_cash_benchmark_no_spurious_alpha(returns):
    m=metrics(returns.MINT,returns.BIL,returns.BIL)
    assert np.isnan(m["alpha_annual"]) and np.isnan(m["beta"])
    assert m["annual_mean_active_return"]==pytest.approx((returns.MINT-returns.BIL).mean()*12)

@pytest.mark.parametrize("profile",list(PROFILES))
def test_optimizer_constraints(returns,profile):
    w,cov=optimize(returns.iloc[:36],PROFILES[profile])
    assert w.sum()==pytest.approx(1)
    assert w.iloc[:3].sum()==pytest.approx(PROFILES[profile],abs=1e-6)
    assert w.min()>=0 and w.max()<=.50001 and w.GLD<=.10001 and w.BIL<=.15001
    assert np.linalg.eigvalsh(cov).min()>0

@pytest.mark.parametrize("equity,cap",[(.05,.5),(.9,.5),(.55,.2),(.55,.8)])
def test_invalid_constraints_fail(returns,equity,cap):
    with pytest.raises(ValueError):optimize(returns,equity,cap)

def test_infeasible_constraints_fail(returns):
    # Equity only 10%; non-equity capacity is 30+30+10+15=85%.
    with pytest.raises(ValueError):optimize(returns,.1,.3)

def test_short_history_fails(returns):
    with pytest.raises(ValueError):optimize(returns.iloc[:12],.55)

def test_policy_fully_invested():
    for e in PROFILES.values():
        w=policy_weights(e)
        assert w.sum()==pytest.approx(1) and w.min()>=0
        assert w.iloc[:3].sum()==pytest.approx(e)

def test_cost_and_drift():
    target=pd.Series([.5,.5]);pre=pd.Series([.8,.2]);r=pd.Series([.1,-.1])
    gross,net,cost,traded,drift=step(target,pre,r,10)
    assert traded==pytest.approx(.6) and cost==pytest.approx(.0006)
    assert gross==pytest.approx(0) and net==pytest.approx(-.0006)
    assert drift.tolist()==pytest.approx([.55,.45])

def test_initial_cash_entry_cost():
    w=pd.Series([.5,.5])
    assert step(w,w*0,w*0,10)[2]==pytest.approx(.001)

def test_backtest_has_no_lookahead(returns):
    p,w=backtest(returns.iloc[:40],lookback=36)
    changed=returns.iloc[:40].copy();changed.iloc[37:]=changed.iloc[37:]*3
    p2,w2=backtest(changed,lookback=36)
    # Holding month 37's weights cannot know returns of that month or later.
    cutoff=returns.index[37]
    pd.testing.assert_frame_equal(w[w.date<=cutoff].reset_index(drop=True),w2[w2.date<=cutoff].reset_index(drop=True))
    assert (pd.to_datetime(p.training_end)<pd.to_datetime(p.date)).all()
    assert (p.net_return<=p.gross_return+1e-12).all()
    assert len(p)==6*4

def test_forecast_features_are_lagged(daily_prices):
    before=features(daily_prices)
    changed=daily_prices.copy()
    date=pd.Timestamp("2020-06-30")
    selected=(changed.ticker=="SPY") & (changed.date>"2020-05-31")
    changed.loc[selected,"adjusted_close"]*=np.linspace(1,1.5,selected.sum())
    after=features(changed)
    pd.testing.assert_series_equal(before.loc[date].drop("target"),after.loc[date].drop("target"))

def test_forecast_walkforward(daily_prices):
    # Small terminal holdout exercises actual model fitting without a long test run.
    frame=features(daily_prices)
    predictions,scores=forecast(daily_prices,minimum_train=len(frame)-3)
    assert set(scores.model)=={"OLS","Random forest","Persistence","Trailing mean"}
    assert len(predictions)==12 and (scores.observations==3).all()
    assert (pd.to_datetime(predictions.training_end)<pd.to_datetime(predictions.date)).all()
    assert (predictions.prediction>=0).all()

def test_fund_comparators(returns):
    f,r=evaluate_funds(returns,{"BOND":"AGG","MINT":"BIL"})
    assert dict(zip(f.fund,f.benchmark_proxy))=={"BOND":"AGG","MINT":"BIL"}
    assert (r.months==36).all()
