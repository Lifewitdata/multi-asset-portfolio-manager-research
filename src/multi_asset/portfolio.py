import cvxpy as cp
import numpy as np
import pandas as pd
from sklearn.covariance import LedoitWolf
from .config import INVESTABLE, PROFILES, LOOKBACK, COST_BPS

def optimize(history, equity_target, cap=0.50):
    if not 0.1 <= equity_target <= 0.85 or not 0.30 <= cap <= 0.70:
        raise ValueError("Equity target must be 10%-85%; per-asset cap 30%-70%")
    data = history[INVESTABLE]
    if len(data) < 24 or not np.isfinite(data.to_numpy()).all():
        raise ValueError("At least 24 complete historical monthly returns required")
    cov = LedoitWolf().fit(data).covariance_
    w = cp.Variable(len(INVESTABLE))
    constraints = [cp.sum(w)==1, w>=0, w<=cap, cp.sum(w[:3])==equity_target,
                   w[5]<=0.10, w[6]<=0.15]
    problem = cp.Problem(cp.Minimize(cp.quad_form(w, cp.psd_wrap(cov))), constraints)
    problem.solve(solver="CLARABEL")
    if problem.status != cp.OPTIMAL or w.value is None:
        raise ValueError(f"Allocation infeasible or solver not optimal: {problem.status}")
    weights = np.maximum(np.asarray(w.value), 0)
    weights /= weights.sum()
    if abs(weights[:3].sum()-equity_target)>1e-5 or weights.max()>cap+1e-5 or weights[5]>.10001 or weights[6]>.15001:
        raise ValueError("Solver constraint violation")
    return pd.Series(weights, index=INVESTABLE), cov

def policy_weights(equity):
    return pd.Series([equity*.6, equity*.25, equity*.15, (1-equity-.1)*.7,
                      (1-equity-.1)*.3, .05, .05], index=INVESTABLE)

def step(target, pretrade, asset_returns, cost_bps=COST_BPS):
    traded = float((target-pretrade).abs().sum())
    cost = traded * cost_bps/10000
    gross = float(target @ asset_returns)
    net = (1-cost)*(1+gross)-1
    drifted = target*(1+asset_returns)/(1+gross)
    return gross, net, cost, traded, drifted

def backtest(returns, lookback=LOOKBACK, cost_bps=COST_BPS):
    records, weights = [], []
    for profile, equity in PROFILES.items():
        for approach in ["Optimized", "Policy"]:
            # Start fully in cash outside the asset holdings; first purchase costs 10bp.
            pretrade = pd.Series(0.0, index=INVESTABLE)
            for i in range(lookback, len(returns)):
                date = returns.index[i]
                history = returns.iloc[i-lookback:i]  # never includes holding-month returns
                target = optimize(history, equity)[0] if approach=="Optimized" else policy_weights(equity)
                gross, net, cost, traded, pretrade = step(target, pretrade, returns.loc[date, INVESTABLE], cost_bps)
                name = f"{profile} {approach}"
                records.append({"date":date,"portfolio":name,"profile":profile,"approach":approach,
                                "gross_return":gross,"net_return":net,"cost":cost,"traded_fraction":traded,
                                "training_end":history.index[-1]})
                weights.extend({"date":date,"portfolio":name,"ticker":ticker,"weight":float(value)} for ticker,value in target.items())
    return pd.DataFrame(records), pd.DataFrame(weights)
