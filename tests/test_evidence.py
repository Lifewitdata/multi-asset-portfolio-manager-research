import numpy as np
import pandas as pd
from multi_asset.config import INVESTABLE
from multi_asset.data import monthly_prices
from multi_asset.evidence import month_end, replay_net_returns, slsqp_weights, cagr, tracking_error, row
from multi_asset.portfolio import backtest, optimize
from multi_asset.analytics import metrics

def test_month_end_matches_pipeline(daily_prices):
    independent, last_dates = month_end(daily_prices)
    pipeline = monthly_prices(daily_prices)
    assert np.allclose(independent[pipeline.columns].to_numpy(), pipeline.to_numpy(), rtol=0, atol=0)
    assert (last_dates.max(axis=1) <= independent.index).all()

def test_replay_reproduces_backtest(returns):
    portfolios, weights = backtest(returns.iloc[:44])
    for name in ["Balanced Optimized", "Growth Policy"]:
        stored = portfolios[portfolios.portfolio==name].set_index("date").net_return
        replayed = replay_net_returns(weights[weights.portfolio==name], returns)
        assert np.abs(replayed-stored).max() < 1e-14

def test_replay_detects_cost_change(returns):
    portfolios, weights = backtest(returns.iloc[:40])
    stored = portfolios[portfolios.portfolio=="Balanced Policy"].set_index("date").net_return
    replayed = replay_net_returns(weights[weights.portfolio=="Balanced Policy"], returns, cost_bps=5)
    assert np.abs(replayed-stored).max() > 1e-6

def test_second_solver_agrees(returns):
    # Synthetic i.i.d. returns give a flat optimum, so compare the objective, not the weights.
    # CLARABEL stops slightly short of SLSQP (measured up to 2.8e-5 relative variance here).
    history = returns[INVESTABLE].tail(36)
    for equity in [0.25, 0.55, 0.80]:
        w, cov = optimize(history, equity)
        alt = slsqp_weights(history, equity)
        assert abs(alt@cov@alt - w@cov@w) <= 1e-4*(w@cov@w)
        assert abs(alt.sum()-1) < 1e-9 and abs(alt.iloc[:3].sum()-equity) < 1e-9

def test_closed_forms_match_analytics(returns):
    result = metrics(returns.SPY, returns.AGG, returns.BIL)
    assert abs(cagr(returns.SPY)-result["cagr"]) < 1e-14
    assert abs(tracking_error(returns.SPY, returns.AGG)-result["tracking_error"]) < 1e-14

def test_stage_status():
    assert row("m","s","x",1.0,1.0+1e-13,1e-12)["status"]=="PASS"
    assert row("m","s","x",1.0,1.0+1e-9,1e-12)["status"]=="FAIL"
    assert row("m","s","x","7.42%","7.43%",0)["status"]=="FAIL"
    assert row("m","s","x",1.0,None,1e-12)["status"]=="NOT RUN"
