import argparse
import json
import hashlib
from pathlib import Path
import pandas as pd
import numpy as np
from .config import ROOT, ASSETS, MANAGERS
from .data import fetch, load, monthly_prices
from .analytics import metrics, evaluate_funds, factor_research
from .portfolio import backtest
from .forecast import forecast

def run(download=False, root=ROOT):
    root = Path(root)
    prices, macro, manifest = fetch(root) if download else load(root)
    monthly = monthly_prices(prices)
    returns = monthly.pct_change(fill_method=None).iloc[1:]
    if returns.isna().any().any():
        raise ValueError("Missing returns; no imputation allowed")
    portfolios, weights = backtest(returns)
    statistics=[]
    for name,g in portfolios.groupby("portfolio"):
        r = g.set_index("date").net_return
        policy = portfolios[portfolios.portfolio==name.split()[0]+" Policy"].set_index("date").net_return
        statistics.append({"portfolio":name, **metrics(r, policy, returns.BIL),
                           "annual_traded_fraction":g.traded_fraction.mean()*12})
    funds, rolling = evaluate_funds(returns, MANAGERS)
    factors, rates, monthly_macro = factor_research(returns, macro)
    predictions, scores = forecast(prices)
    assets = pd.DataFrame([{"ticker":t,"name":n,"asset_class":c} for t,(n,c) in ASSETS.items()])
    outputs = {"assets":assets,"monthly_prices":monthly.reset_index(),"monthly_returns":returns.reset_index(),
               "monthly_macro":monthly_macro.reset_index(),"portfolio_returns":portfolios,"weights":weights,
               "portfolio_metrics":pd.DataFrame(statistics),"fund_metrics":funds,"rolling_fund_metrics":rolling,
               "factor_coefficients":factors,"rate_sensitivity":rates,"volatility_predictions":predictions,"volatility_scores":scores}
    processed=root/"data/processed";processed.mkdir(parents=True,exist_ok=True)
    for name,frame in outputs.items():
        frame.to_csv(processed/f"{name}.csv",index=False)
    facts={"data_type":"real_historical","instruments":len(ASSETS),"daily_price_rows":len(prices),
           "monthly_return_rows":len(returns),"backtest_months":int(portfolios.groupby("portfolio").size().iloc[0]),
           "return_start":str(returns.index[0].date()),"return_end":str(returns.index[-1].date()),
           "best_volatility_model_by_mae":str(scores.iloc[0].model),"forecast_months":int(scores.iloc[0].observations)}
    report=root/"reports/local";report.mkdir(parents=True,exist_ok=True)
    (report/"research_facts.json").write_text(json.dumps(facts,indent=2))
    quality={**facts,"duplicate_price_keys":int(prices.duplicated(["date","ticker"]).sum()),
             "missing_monthly_prices":int(monthly.isna().sum().sum()),"source_manifest":manifest,
             "processed_sha256":{f.name:hashlib.sha256(f.read_bytes()).hexdigest() for f in sorted(processed.glob('*.csv'))}}
    (report/"data_quality.json").write_text(json.dumps(quality,indent=2))
    lines=["# Historical portfolio research brief", "",f"Study: {facts['return_start']} to {facts['return_end']}; {facts['backtest_months']} holding months after the training window.",
           "", "## Client allocation comparison", "", "Net returns include modelled trading costs. Each optimized profile has its own equity-matched policy comparator.", ""]
    for row in statistics:
        lines.append(f"- {row['portfolio']}: CAGR {row['cagr']:.2%}, volatility {row['annual_volatility']:.2%}, maximum drawdown {row['maximum_drawdown']:.2%}.")
    lines += ["", "## Active fund evaluation", "", "These are fund-level market-price comparisons. Benchmark proxies are not official indexes or manager-tenure attribution.", ""]
    for row in funds.to_dict('records'):
        alpha = f"annual OLS alpha {row['alpha_annual']:.2%} (HAC p-value {row['alpha_pvalue_hac']:.3f})" if np.isfinite(row['alpha_annual']) else "alpha/beta not identified because the comparator is also the cash proxy"
        lines.append(f"- {row['fund']} versus {row['benchmark_proxy']}: annual tracking error {row['tracking_error']:.2%}, information ratio {row['information_ratio']:.2f}, annual mean active return {row['annual_mean_active_return']:.2%}; {alpha}.")
    lines += ["", "## Forecast validation", "", f"Lowest walk-forward MAE: {facts['best_volatility_model_by_mae']}; {facts['forecast_months']} forecast months. The model is not used to trade the portfolios.", ""]
    for row in scores.to_dict('records'):
        lines.append(f"- {row['model']}: MAE {row['mae']:.4f}; RMSE {row['rmse']:.4f} in annualized volatility decimal units.")
    lines += ["", "## Interpretation and next research", "", "Compare volatility and drawdown against the relevant policy before treating higher returns as improvement. Investigate factor exposures and benchmark mismatch before attributing active return to skill. Test different cost and training-window assumptions before selecting a portfolio.", "", "## Limits", "", "Retrospectively selected surviving ETFs; adjusted prices can be revised. USD unhedged market-price total-return proxies, not official NAV returns. No taxes, bid/ask spreads, currency hedging or intramonth drawdowns. Trading at observed month-end prices is idealized. Profiles are illustrative, not client advice. Current FRED history is not a vintage database. Credit factor is not duration-neutral. No individual manager attribution or future-performance claim."]
    (report/"executive_summary.md").write_text("\n".join(lines)+"\n")
    print(json.dumps(facts,indent=2))
    return outputs, facts

if __name__=="__main__":
    parser=argparse.ArgumentParser();parser.add_argument("--download",action="store_true")
    run(parser.parse_args().download)
