"""Source-to-screen calculation evidence for three dashboard metrics.

Each metric is traced from hash-verified raw observations, through an independent
recompute, the pipeline CSV, SQL Server (stored value plus a T-SQL recompute) and
the value the Dash callback actually renders.
"""
import argparse
import os
from contextlib import contextmanager
from datetime import datetime, timezone
import numpy as np
import pandas as pd
from scipy.optimize import minimize
from sklearn.covariance import LedoitWolf
from sqlalchemy import text
from .config import ROOT, INVESTABLE, PROFILES, LOOKBACK, COST_BPS, START, END
from .data import load, parse_yahoo, verify_processed
from .portfolio import optimize

PORTFOLIO = "Balanced Optimized"
FUND, BENCHMARK = "BOND", "AGG"
WEIGHT_TICKER = "SPY"
EXACT = 1e-12      # same IEEE doubles moved between CSV, SQL and Dash
TSQL = 1e-10       # T-SQL LOG/EXP/STDEV evaluate in a different order
SOLVER = 1e-4      # two different QP solvers on the same covariance
REPORT = ROOT/"reports/calculation_evidence.md"

def month_end(prices):
    """Last observation per calendar month, written without resample() so it is independent of data.monthly_prices."""
    p = prices.sort_values("date")
    p = p.assign(month=p.date.dt.to_period("M"))
    last = p.groupby(["ticker", "month"]).tail(1)
    wide = last.pivot(index="month", columns="ticker", values="adjusted_close")
    dates = last.pivot(index="month", columns="ticker", values="date")
    wide.index = wide.index.to_timestamp("M")
    dates.index = wide.index
    return wide.sort_index(), dates.sort_index()

def replay_net_returns(weights, returns, cost_bps=COST_BPS):
    """Rebuild net returns from stored target weights: buys and sells both pay cost_bps per dollar."""
    pretrade = pd.Series(0.0, index=INVESTABLE)
    out = {}
    for date, group in weights.groupby("date", sort=True):
        target = group.set_index("ticker").weight.reindex(INVESTABLE)
        r = returns.loc[date, INVESTABLE]
        cost = np.abs(target-pretrade).sum()*cost_bps/10000
        gross = float(np.dot(target, r))
        out[date] = (1-cost)*(1+gross)-1
        pretrade = target*(1+r)/(1+gross)
    return pd.Series(out).sort_index()

def cagr(r):
    return float(np.prod(1+np.asarray(r))**(12/len(r))-1)

def tracking_error(r, b):
    return float(np.std(np.asarray(r)-np.asarray(b), ddof=1)*np.sqrt(12))

def slsqp_weights(history, equity, cap=0.50):
    """Same problem as portfolio.optimize, solved by SciPy SLSQP instead of CVXPY/CLARABEL."""
    cov = LedoitWolf().fit(history[INVESTABLE]).covariance_
    n = len(INVESTABLE)
    constraints = [{"type":"eq","fun":lambda w:w.sum()-1},
                   {"type":"eq","fun":lambda w:w[:3].sum()-equity},
                   {"type":"ineq","fun":lambda w:0.10-w[5]},
                   {"type":"ineq","fun":lambda w:0.15-w[6]}]
    start = np.r_[np.full(3, equity/3), np.full(n-3, (1-equity)/(n-3))]
    fit = minimize(lambda w:w@cov@w, start, jac=lambda w:2*cov@w, method="SLSQP",
                   bounds=[(0, cap)]*n, constraints=constraints, options={"ftol":1e-15,"maxiter":1000})
    if not fit.success:
        raise ValueError(f"SLSQP failed: {fit.message}")
    return pd.Series(fit.x, index=INVESTABLE)

def card_value(cards, label):
    for card in cards:
        span, strong = card.children
        if span.children == label:
            return strong.children
    raise KeyError(label)

def bar_value(figure, name):
    for trace in figure.data:
        if trace.name == name:
            return float(trace.y[0])
    raise KeyError(name)

@contextmanager
def dash_source(mode):
    previous = os.environ.get("MULTI_ASSET_DASH_SOURCE")
    os.environ["MULTI_ASSET_DASH_SOURCE"] = mode
    try:
        yield
    finally:
        if previous is None:
            os.environ.pop("MULTI_ASSET_DASH_SOURCE")
        else:
            os.environ["MULTI_ASSET_DASH_SOURCE"] = previous

def row(metric, stage, source, expected, actual, tolerance):
    if actual is None:
        return {"metric":metric,"stage":stage,"source":source,"expected":expected,"actual":None,
                "difference":None,"tolerance":tolerance,"status":"NOT RUN"}
    if isinstance(expected, str):
        diff = 0.0 if expected == actual else None
        ok = expected == actual
    else:
        diff = abs(float(actual)-float(expected))
        ok = diff <= tolerance
    return {"metric":metric,"stage":stage,"source":source,"expected":expected,"actual":actual,
            "difference":diff,"tolerance":tolerance,"status":"PASS" if ok else "FAIL"}

def raw_agreement(prices, tickers, root=ROOT):
    """Max |Yahoo JSON adjclose - prices.csv| over every study-period observation of the tickers."""
    worst, count = 0.0, 0
    for t in tickers:
        payload = (root/f"data/raw/yahoo_{t}.json").read_bytes()
        source = parse_yahoo(payload, t)
        source = source[source.date.between(START, END)]
        joined = source.merge(prices[prices.ticker==t], on=["date","ticker"], how="outer", suffixes=("_json","_csv"), indicator=True)
        if (joined._merge != "both").any():
            raise ValueError(f"Yahoo JSON and prices.csv disagree on dates for {t}")
        worst = max(worst, float((joined.adjusted_close_json-joined.adjusted_close_csv).abs().max()))
        count += len(joined)
    return worst, count

def build(sql=None, root=ROOT):
    prices, _, manifest = load(root)  # raises unless every raw file matches its manifest sha256
    verify_processed(root)
    month, last_dates = month_end(prices)
    returns = month.pct_change(fill_method=None).iloc[1:]
    processed = {n:pd.read_csv(root/f"data/processed/{n}.csv", parse_dates=["date"]) for n in ["monthly_returns","portfolio_returns","weights"]}
    processed |= {n:pd.read_csv(root/f"data/processed/{n}.csv") for n in ["portfolio_metrics","fund_metrics"]}
    pipeline_returns = processed["monthly_returns"].set_index("date")
    rows, samples = [], {}
    with dash_source("csv"):
        from .dashboard import load_tables, portfolio_view, fund_view
        csv_tables = load_tables()
    sql_tables = None
    if sql is not None:
        with dash_source("sqlserver"):
            sql_tables = load_tables()

    # Shared upstream stage: independent month-end returns equal the pipeline's monthly_returns.csv.
    upstream = float((returns[pipeline_returns.columns]-pipeline_returns).abs().max().max())

    # A. Balanced Optimized net CAGR (KPI card)
    m = "A. Balanced Optimized net CAGR"
    worst, n = raw_agreement(prices, INVESTABLE, root)
    rows.append(row(m, "1 raw: Yahoo JSON adjclose = prices.csv", f"{n} daily observations, 7 investable ETFs", 0.0, worst, EXACT))
    rows.append(row(m, "2 independent month-end returns = monthly_returns.csv", "max abs diff, 144 months x 10 tickers", 0.0, upstream, EXACT))
    w = processed["weights"][processed["weights"].portfolio==PORTFOLIO]
    net = replay_net_returns(w, returns)
    stored_net = processed["portfolio_returns"].query("portfolio==@PORTFOLIO").set_index("date").net_return.sort_index()
    rows.append(row(m, "3 replayed net returns = portfolio_returns.csv", f"max abs diff over {len(net)} holding months", 0.0,
                    float((net-stored_net).abs().max()), EXACT))
    expected = cagr(net)
    pm = processed["portfolio_metrics"].set_index("portfolio")
    rows.append(row(m, "4 pipeline CSV", "portfolio_metrics.csv cagr", expected, float(pm.loc[PORTFOLIO,"cagr"]), EXACT))
    sql_stored = sql_recompute = None
    if sql is not None:
        with sql.connect() as conn:
            sql_stored = conn.execute(text("SELECT cagr FROM research.portfolio_metrics WHERE portfolio=:p"), {"p":PORTFOLIO}).scalar_one()
            sql_recompute = conn.execute(text("SELECT POWER(EXP(SUM(LOG(1+net_return))), 12.0/COUNT(*))-1 FROM research.portfolio_returns WHERE portfolio=:p"), {"p":PORTFOLIO}).scalar_one()
    rows.append(row(m, "5 SQL stored", "research.portfolio_metrics.cagr", expected, sql_stored, EXACT))
    rows.append(row(m, "6 SQL recompute", "EXP(SUM(LOG(1+net_return)))^(12/n)-1", expected, sql_recompute, TSQL))
    shown = f"{expected:.2%}"
    rows.append(row(m, "7 Dash KPI card, CSV mode", "portfolio_view 'Net CAGR'", shown, card_value(portfolio_view(csv_tables,"Balanced")[0],"Net CAGR"), 0))
    rows.append(row(m, "8 Dash KPI card, SQL mode", "portfolio_view 'Net CAGR'", shown,
                    card_value(portfolio_view(sql_tables,"Balanced")[0],"Net CAGR") if sql_tables else None, 0))
    samples[m] = month[INVESTABLE].iloc[[0,1,-2,-1]]

    # B. BOND tracking error versus AGG (fund table)
    m = "B. BOND tracking error vs AGG"
    worst, n = raw_agreement(prices, [FUND, BENCHMARK], root)
    rows.append(row(m, "1 raw: Yahoo JSON adjclose = prices.csv", f"{n} daily observations, BOND and AGG", 0.0, worst, EXACT))
    rows.append(row(m, "2 independent month-end returns = monthly_returns.csv", "max abs diff, BOND and AGG",
                    0.0, float((returns[[FUND,BENCHMARK]]-pipeline_returns[[FUND,BENCHMARK]]).abs().max().max()), EXACT))
    expected = tracking_error(returns[FUND], returns[BENCHMARK])
    fm = processed["fund_metrics"].set_index("fund")
    rows.append(row(m, "3 pipeline CSV", "fund_metrics.csv tracking_error", expected, float(fm.loc[FUND,"tracking_error"]), EXACT))
    sql_stored = sql_recompute = None
    if sql is not None:
        with sql.connect() as conn:
            sql_stored = conn.execute(text("SELECT tracking_error FROM research.fund_metrics WHERE fund=:f"), {"f":FUND}).scalar_one()
            sql_recompute = conn.execute(text("SELECT STDEV([BOND]-[AGG])*SQRT(12.0) FROM research.monthly_returns")).scalar_one()
    rows.append(row(m, "4 SQL stored", "research.fund_metrics.tracking_error", expected, sql_stored, EXACT))
    rows.append(row(m, "5 SQL recompute", "STDEV(BOND-AGG)*SQRT(12) over research.monthly_returns", expected, sql_recompute, TSQL))
    shown = round(expected, 5)
    rows.append(row(m, "6 Dash fund table, CSV mode", "fund_view grid, rounded to 5 dp", shown, fund_view(csv_tables,FUND)[0].rowData[0]["tracking_error"], EXACT))
    rows.append(row(m, "7 Dash fund table, SQL mode", "fund_view grid, rounded to 5 dp", shown,
                    fund_view(sql_tables,FUND)[0].rowData[0]["tracking_error"] if sql_tables else None, EXACT))
    samples[m] = month[[FUND,BENCHMARK]].iloc[[0,1,-2,-1]]

    # C. Balanced Optimized SPY weight at the last rebalance (allocation chart)
    m = "C. Balanced Optimized last-rebalance SPY weight"
    last = w.date.max()
    i = returns.index.get_loc(last)
    history = returns.iloc[i-LOOKBACK:i]
    independent = slsqp_weights(history, PROFILES["Balanced"])
    expected = float(independent[WEIGHT_TICKER])
    rerun_weights, cov = optimize(history, PROFILES["Balanced"])
    rerun = float(rerun_weights[WEIGHT_TICKER])
    stored = float(w[w.date==last].set_index("ticker").weight[WEIGHT_TICKER])
    window_diff = float((history[INVESTABLE]-pipeline_returns.loc[history.index, INVESTABLE]).abs().max().max())
    rows.append(row(m, "1 independent window returns = monthly_returns.csv", f"{LOOKBACK} months {history.index[0]:%Y-%m} to {history.index[-1]:%Y-%m}, 7 ETFs", 0.0, window_diff, EXACT))
    best = float(independent@cov@independent)
    rows.append(row(m, "2a portfolio variance, CVXPY vs SciPy SLSQP", "monthly variance; tolerance is 1e-4 relative", best,
                    float(rerun_weights@cov@rerun_weights), 1e-4*best))
    rows.append(row(m, "2b SPY weight, CVXPY re-run vs SciPy SLSQP", "same Ledoit-Wolf covariance, different solver", expected, rerun, SOLVER))
    rows.append(row(m, "3 pipeline CSV", f"weights.csv {last:%Y-%m-%d}", rerun, stored, 1e-8))
    sql_stored = sql_sum = None
    if sql is not None:
        with sql.connect() as conn:
            sql_stored = conn.execute(text("SELECT weight FROM research.weights WHERE portfolio=:p AND ticker=:t AND [date]=(SELECT MAX([date]) FROM research.weights WHERE portfolio=:p)"), {"p":PORTFOLIO,"t":WEIGHT_TICKER}).scalar_one()
            sql_sum = conn.execute(text("SELECT SUM(weight) FROM research.weights WHERE portfolio=:p AND [date]=(SELECT MAX([date]) FROM research.weights WHERE portfolio=:p)"), {"p":PORTFOLIO}).scalar_one()
    rows.append(row(m, "4 SQL stored", "research.weights, latest date", stored, sql_stored, EXACT))
    rows.append(row(m, "5 SQL check: weights sum to 1", "SUM(weight) at latest date (optimizer is not re-run in T-SQL)", 1.0, sql_sum, 1e-9))
    rows.append(row(m, "6 Dash allocation bar, CSV mode", "portfolio_view allocation trace 'SPY'", stored, bar_value(portfolio_view(csv_tables,"Balanced")[3],WEIGHT_TICKER), EXACT))
    rows.append(row(m, "7 Dash allocation bar, SQL mode", "portfolio_view allocation trace 'SPY'", stored,
                    bar_value(portfolio_view(sql_tables,"Balanced")[3],WEIGHT_TICKER) if sql_tables else None, EXACT))
    samples[m] = month[INVESTABLE].loc[[history.index[0]-pd.offsets.MonthEnd(1), history.index[0], history.index[-1]]]

    raw = {r["file"]:r["sha256"] for r in manifest if r["file"] in {"prices.csv"} | {f"yahoo_{t}.json" for t in INVESTABLE+[FUND,BENCHMARK]}}
    return rows, samples, last_dates, raw, independent, rerun

def fmt(value):
    if value is None:
        return "-"
    if isinstance(value, str):
        return value
    return f"{value:.3e}" if value != 0 and abs(value) < 1e-4 else f"{value:.12g}"

def render(rows, samples, last_dates, raw, independent, sql_label):
    status = "PASS" if all(r["status"]=="PASS" for r in rows) else ("FAIL" if any(r["status"]=="FAIL" for r in rows) else "PASS (SQL stages not run)")
    lines = ["# Source-to-screen calculation evidence", "",
             f"Generated {datetime.now(timezone.utc):%Y-%m-%d %H:%M} UTC by `python -m multi_asset.evidence`. SQL source: {sql_label}. Overall: **{status}**.", "",
             "Each stage compares an expected value with the value actually found at that stage. "
             "\"Expected\" is an independent recompute written in `src/multi_asset/evidence.py` rather than a copy of the pipeline result, "
             "except where noted. Tolerances: 1e-12 for values moved between CSV, SQL and Dash; 1e-10 for T-SQL recomputes; "
             "1e-4 for comparing two different optimizers.", "",
             "Raw inputs were verified against `data/raw/manifest.json` before anything was read:", "",
             "| File | sha256 |", "|---|---|"]
    lines += [f"| {f} | `{h[:16]}…` |" for f,h in sorted(raw.items())]
    for metric in dict.fromkeys(r["metric"] for r in rows):
        lines += ["", f"## {metric}", "", "| Stage | Source | Expected | Actual | Difference | Tolerance | Status |", "|---|---|---:|---:|---:|---:|---|"]
        for r in (r for r in rows if r["metric"]==metric):
            lines.append(f"| {r['stage']} | {r['source']} | {fmt(r['expected'])} | {fmt(r['actual'])} | {fmt(r['difference'])} | {fmt(r['tolerance'])} | {r['status']} |")
        sample = samples[metric]
        lines += ["", "Month-end adjusted closes used (last trading day of each month; Yahoo adjusted close, USD):", "",
                  "| Month end | " + " | ".join(sample.columns) + " |", "|---|" + "---:|"*len(sample.columns)]
        for date, values in sample.iterrows():
            obs = last_dates.loc[date, sample.columns]
            lines.append(f"| {date:%Y-%m-%d} | " + " | ".join(f"{v:.4f} ({d:%m-%d})" for v,d in zip(values, obs)) + " |")
        if metric.startswith("C."):
            lines += ["", "Full SLSQP solution for the last rebalance: " + ", ".join(f"{t} {v:.4%}" for t,v in independent.items()) + "."]
    lines += ["", "## How to read this", "",
              "- Stage 1 proves the parsed raw provider file and the normalized cache are the same numbers.",
              "- The middle stages prove the pipeline formula: returns are recomputed from month-end prices, net returns are replayed from stored weights with 10bp per dollar traded, and the optimizer is checked against a second solver.",
              "- SQL stages prove SQL Server stores the same value and that a recompute in T-SQL lands on it.",
              "- Dash stages call the real callback functions (`portfolio_view`, `fund_view`) and read the rendered value: the KPI card text, the grid cell and the bar height.",
              "- NOT RUN means `MULTI_ASSET_SQLSERVER_URL` was not set when the report was generated.",
              "", "Prices quoted above are a handful of illustrative observations from the provider; see `docs/data_usage_register.md`."]
    return "\n".join(lines)+"\n"

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", default=str(REPORT))
    args = parser.parse_args()
    sql, label = None, "not configured (SQL stages NOT RUN)"
    if os.getenv("MULTI_ASSET_SQLSERVER_URL"):
        from .database import engine
        sql = engine()
        label = f"SQL Server database `{sql.url.database}` on `{sql.url.host}`"
    try:
        rows, samples, last_dates, raw, independent, _ = build(sql)
    finally:
        if sql is not None:
            sql.dispose()
    with open(args.output, "w", encoding="utf-8", newline="\n") as handle:
        handle.write(render(rows, samples, last_dates, raw, independent, label))
    for r in rows:
        print(f"{r['status']:8} {r['metric'][:2]} {r['stage']}")
    if any(r["status"]=="FAIL" for r in rows):
        raise SystemExit(1)

if __name__ == "__main__":
    main()
