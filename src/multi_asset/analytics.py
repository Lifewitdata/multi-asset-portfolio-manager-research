import numpy as np
import pandas as pd
import statsmodels.api as sm

def drawdown(returns):
    wealth = (1 + returns).cumprod()
    peak = wealth.cummax().clip(lower=1.0)  # include initial wealth: first-month loss counts
    return wealth / peak - 1

def metrics(returns, benchmark, cash):
    frame = pd.concat([returns.rename("r"), benchmark.rename("b"), cash.rename("c")], axis=1).dropna()
    r, b, c = frame.r, frame.b, frame.c
    if len(r) < 3 or not np.isfinite(frame.to_numpy()).all() or (frame <= -1).any().any():
        raise ValueError("Insufficient or invalid returns")
    active = r - b
    excess = r - c
    vol, te = r.std(ddof=1) * np.sqrt(12), active.std(ddof=1) * np.sqrt(12)
    alpha, alpha_pvalue, beta = np.nan, np.nan, np.nan
    # BIL is both the MINT comparator and the cash proxy. A zero benchmark
    # excess series cannot identify beta or a risk-adjusted Jensen alpha.
    if (b-c).std(ddof=1) > 1e-12:
        x = sm.add_constant((b-c).rename("benchmark_excess"), has_constant="add")
        fit = sm.OLS(excess, x).fit(cov_type="HAC", cov_kwds={"maxlags": 3})
        alpha, alpha_pvalue, beta = fit.params["const"]*12, fit.pvalues["const"], fit.params["benchmark_excess"]
    return {"months": len(r), "cagr": (1+r).prod()**(12/len(r))-1,
            "annual_volatility": vol, "maximum_drawdown": drawdown(r).min(),
            "sharpe_cash_proxy": excess.mean()*12/vol if vol > 1e-12 else np.nan,
            "tracking_error": te, "information_ratio": active.mean()*12/te if te > 1e-12 else np.nan,
            "alpha_annual": alpha, "alpha_pvalue_hac": alpha_pvalue,
            "beta": beta, "annual_mean_active_return": active.mean()*12,
            "active_month_hit_rate": (active>0).mean()}

def evaluate_funds(returns, mapping):
    rows, rolling = [], []
    for fund, benchmark in mapping.items():
        result = metrics(returns[fund], returns[benchmark], returns.BIL)
        rows.append({"fund": fund, "benchmark_proxy": benchmark, **result})
        for date in returns.index[35:]:
            sample = returns.loc[:date].tail(36)
            stats = metrics(sample[fund], sample[benchmark], sample.BIL)
            rolling.append({"date": date, "fund": fund, **stats})
    return pd.DataFrame(rows), pd.DataFrame(rolling)

def factor_research(returns, macro):
    # Contemporaneous attribution, not a forecasting signal. Credit proxy is not duration-neutral.
    m = macro.pivot(index="date", columns="series", values="value").sort_index().resample("ME").last()
    if m.reindex(returns.index).isna().any().any():
        raise ValueError("Incomplete monthly macro coverage")
    factors = pd.DataFrame({"equity_excess": returns.SPY-returns.BIL,
                            "treasury_excess": returns.IEF-returns.BIL,
                            "credit_relative": returns.LQD-returns.IEF})
    rows = []
    for fund in ["BOND", "MINT"]:
        joined = factors.join((returns[fund]-returns.BIL).rename("target")).dropna()
        x = sm.add_constant(joined.drop(columns="target"))
        fit = sm.OLS(joined.target, x).fit(cov_type="HAC", cov_kwds={"maxlags": 3})
        ci = fit.conf_int()
        for term in x.columns:
            rows.append({"fund": fund, "term": term, "coefficient": fit.params[term],
                         "pvalue_hac": fit.pvalues[term], "ci_low": ci.loc[term,0], "ci_high": ci.loc[term,1],
                         "r_squared": fit.rsquared, "nobs": int(fit.nobs)})
    rates = []
    for fund in ["IEF", "LQD", "BOND", "MINT"]:
        joined = pd.concat([(returns[fund]-returns.BIL).rename("target"), m.DGS10.diff().rename("yield_change_pp")], axis=1).dropna()
        fit = sm.OLS(joined.target, sm.add_constant(joined.yield_change_pp)).fit(cov_type="HAC",cov_kwds={"maxlags":3})
        rates.append({"fund":fund, "return_per_1pp_yield_change":fit.params["yield_change_pp"],
                      "pvalue_hac":fit.pvalues["yield_change_pp"], "r_squared":fit.rsquared})
    return pd.DataFrame(rows), pd.DataFrame(rates), m
