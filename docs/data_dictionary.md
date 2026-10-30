# Data dictionary

All return, volatility, weight and alpha fields use **decimal units** (0.05 = 5%) unless stated otherwise. Dates in monthly tables are calendar month end, based on the last available trading observation. Every file below is generated locally.

Field-level source, formula, units, null rule, owner and verification status are in the [field catalog](field_catalog.md). Source permissions and unknowns are in the [data usage register](data_usage_register.md).

| Dataset | Grain / key | Meaning |
|---|---|---|
| `raw/prices.csv` | date, ticker | Positive daily `adjusted_close`, USD market-price basis |
| `raw/macro.csv` | date, series | `value` in percent for DGS10/DGS2; non-observation days omitted |
| `raw/manifest.json` | source file | Retrieval URL, UTC timestamp, normalized row count, SHA-256 |
| `assets.csv` | ticker | Research name and asset class; not an issuer-security master |
| `monthly_prices.csv` | date, one column per ticker | Last observed adjusted close in each month |
| `monthly_returns.csv` | date, one column per ticker | Monthly price-ratio returns; wide analytics matrix |
| `monthly_macro.csv` | date | Month-end DGS10/DGS2 in percent |
| `portfolio_returns.csv` | date, portfolio | Profile/approach, gross and net return, trading cost, traded fraction, training end |
| `weights.csv` | date, portfolio, ticker | Beginning-of-holding-month target weight, before return-driven drift |
| `portfolio_metrics.csv` | portfolio | CAGR, volatility, drawdown, policy-relative statistics, annual traded fraction |
| `fund_metrics.csv` | fund | Full-study statistics and benchmark proxy; no personal-manager tenure |
| `rolling_fund_metrics.csv` | date, fund | Trailing 36-month fund statistics |
| `factor_coefficients.csv` | fund, term | Monthly regression coefficient, HAC p-value and 95% CI, R², sample count |
| `rate_sensitivity.csv` | fund | Return sensitivity to one percentage-point DGS10 change; not duration |
| `volatility_predictions.csv` | date, model | Annualized volatility actual/prediction, last training label date, training-row count |
| `volatility_scores.csv` | model | MAE, RMSE in annualized volatility decimal units, forecast count |
| `research_facts.json` | metric key | Small computed fact set for AI review |
| `data_quality.json` | audit run | Source manifest, coverage checks and processed-output hashes |

`alpha_annual` is 12 × monthly OLS intercept. `annual_mean_active_return` is 12 × arithmetic mean of fund-minus-comparator returns. These are different measures. `information_ratio`, alpha/beta and associated p-values may be null when undefined. For MINT/BIL, alpha/beta are intentionally null because benchmark excess return is zero.

SQL Server stores selected outputs in schema `research`, including normalized daily observations and holdings plus wide monthly analytics. CSV-only notebook inputs (monthly prices, monthly macro and individual forecast predictions) remain reproducible local outputs. Dashboard tables are all supported in both CSV and SQL modes.
