# Source-to-screen calculation evidence

Generated 2026-10-30 17:28 UTC by `python -m multi_asset.evidence`. SQL source: SQL Server database `MultiAssetResearch` on `localhost`. Overall: **PASS**.

Each stage compares an expected value with the value actually found at that stage. "Expected" is an independent recompute written in `src/multi_asset/evidence.py` rather than a copy of the pipeline result, except where noted. Tolerances: 1e-12 for values moved between CSV, SQL and Dash; 1e-10 for T-SQL recomputes; 1e-4 for comparing two different optimizers.

Raw inputs were verified against `data/raw/manifest.json` before anything was read:

| File | sha256 |
|---|---|
| prices.csv | `bc3dde19397be10e…` |
| yahoo_AGG.json | `8c34101851390751…` |
| yahoo_BIL.json | `0d6f0905aa31b718…` |
| yahoo_BOND.json | `e228efb07440058d…` |
| yahoo_EEM.json | `6ab13edbf1d85e83…` |
| yahoo_EFA.json | `6278bbb3816d1177…` |
| yahoo_GLD.json | `1ac0a1a6ccc72078…` |
| yahoo_IEF.json | `72c561beabc49218…` |
| yahoo_LQD.json | `7d69fc7ed1e7cf0d…` |
| yahoo_SPY.json | `6342a7c04131d4d1…` |

## A. Balanced Optimized net CAGR

| Stage | Source | Expected | Actual | Difference | Tolerance | Status |
|---|---|---:|---:|---:|---:|---|
| 1 raw: Yahoo JSON adjclose = prices.csv | 21273 daily observations, 7 investable ETFs | 0 | 5.684e-14 | 5.684e-14 | 1.000e-12 | PASS |
| 2 independent month-end returns = monthly_returns.csv | max abs diff, 144 months x 10 tickers | 0 | 9.920e-17 | 9.920e-17 | 1.000e-12 | PASS |
| 3 replayed net returns = portfolio_returns.csv | max abs diff over 108 holding months | 0 | 2.151e-16 | 2.151e-16 | 1.000e-12 | PASS |
| 4 pipeline CSV | portfolio_metrics.csv cagr | 0.0742386322691 | 0.0742386322691 | 0 | 1.000e-12 | PASS |
| 5 SQL stored | research.portfolio_metrics.cagr | 0.0742386322691 | 0.0742386322691 | 0 | 1.000e-12 | PASS |
| 6 SQL recompute | EXP(SUM(LOG(1+net_return)))^(12/n)-1 | 0.0742386322691 | 0.074238632269 | 7.661e-14 | 1.000e-10 | PASS |
| 7 Dash KPI card, CSV mode | portfolio_view 'Net CAGR' | 7.42% | 7.42% | 0 | 0 | PASS |
| 8 Dash KPI card, SQL mode | portfolio_view 'Net CAGR' | 7.42% | 7.42% | 0 | 0 | PASS |

Month-end adjusted closes used (last trading day of each month; Yahoo adjusted close, USD):

| Month end | SPY | EFA | EEM | IEF | LQD | GLD | BIL |
|---|---:|---:|---:|---:|---:|---:|---:|
| 2013-12-31 | 149.2619 (12-31) | 46.1416 (12-31) | 31.8446 (12-31) | 74.3114 (12-31) | 72.8462 (12-31) | 116.1200 (12-31) | 72.8904 (12-31) |
| 2014-01-31 | 144.0006 (01-31) | 43.7417 (01-31) | 29.0944 (01-31) | 76.5877 (01-31) | 74.2177 (01-31) | 120.0900 (01-31) | 72.8904 (01-31) |
| 2025-11-30 | 676.0958 (11-28) | 92.0393 (11-28) | 53.2767 (11-28) | 94.0458 (11-28) | 107.1636 (11-28) | 387.8800 (11-28) | 88.7134 (11-28) |
| 2025-12-31 | 676.6350 (12-31) | 94.5340 (12-31) | 54.4271 (12-31) | 93.3299 (12-31) | 106.3733 (12-31) | 396.3100 (12-31) | 89.0108 (12-31) |

## B. BOND tracking error vs AGG

| Stage | Source | Expected | Actual | Difference | Tolerance | Status |
|---|---|---:|---:|---:|---:|---|
| 1 raw: Yahoo JSON adjclose = prices.csv | 6078 daily observations, BOND and AGG | 0 | 1.421e-14 | 1.421e-14 | 1.000e-12 | PASS |
| 2 independent month-end returns = monthly_returns.csv | max abs diff, BOND and AGG | 0 | 9.888e-17 | 9.888e-17 | 1.000e-12 | PASS |
| 3 pipeline CSV | fund_metrics.csv tracking_error | 0.0178301153419 | 0.0178301153419 | 6.592e-17 | 1.000e-12 | PASS |
| 4 SQL stored | research.fund_metrics.tracking_error | 0.0178301153419 | 0.0178301153419 | 6.592e-17 | 1.000e-12 | PASS |
| 5 SQL recompute | STDEV(BOND-AGG)*SQRT(12) over research.monthly_returns | 0.0178301153419 | 0.0178301153419 | 1.041e-17 | 1.000e-10 | PASS |
| 6 Dash fund table, CSV mode | fund_view grid, rounded to 5 dp | 0.01783 | 0.01783 | 0 | 1.000e-12 | PASS |
| 7 Dash fund table, SQL mode | fund_view grid, rounded to 5 dp | 0.01783 | 0.01783 | 0 | 1.000e-12 | PASS |

Month-end adjusted closes used (last trading day of each month; Yahoo adjusted close, USD):

| Month end | BOND | AGG |
|---|---:|---:|
| 2013-12-31 | 65.4125 (12-31) | 74.8180 (12-31) |
| 2014-01-31 | 66.4368 (01-31) | 75.9708 (01-31) |
| 2025-11-30 | 89.6413 (11-28) | 97.1714 (11-28) |
| 2025-12-31 | 89.5542 (12-31) | 96.9003 (12-31) |

## C. Balanced Optimized last-rebalance SPY weight

| Stage | Source | Expected | Actual | Difference | Tolerance | Status |
|---|---|---:|---:|---:|---:|---|
| 1 independent window returns = monthly_returns.csv | 36 months 2022-12 to 2025-11, 7 ETFs | 0 | 9.714e-17 | 9.714e-17 | 1.000e-12 | PASS |
| 2a portfolio variance, CVXPY vs SciPy SLSQP | monthly variance; tolerance is 1e-4 relative | 0.000469564337091 | 0.000469564596887 | 2.598e-10 | 4.696e-08 | PASS |
| 2b SPY weight, CVXPY re-run vs SciPy SLSQP | same Ledoit-Wolf covariance, different solver | 0.31372407415 | 0.3137228895 | 1.185e-06 | 0.0001 | PASS |
| 3 pipeline CSV | weights.csv 2025-12-31 | 0.3137228895 | 0.3137228895 | 5.551e-17 | 1.000e-08 | PASS |
| 4 SQL stored | research.weights, latest date | 0.3137228895 | 0.3137228895 | 0 | 1.000e-12 | PASS |
| 5 SQL check: weights sum to 1 | SUM(weight) at latest date (optimizer is not re-run in T-SQL) | 1 | 1 | 2.220e-16 | 1.000e-09 | PASS |
| 6 Dash allocation bar, CSV mode | portfolio_view allocation trace 'SPY' | 0.3137228895 | 0.3137228895 | 0 | 1.000e-12 | PASS |
| 7 Dash allocation bar, SQL mode | portfolio_view allocation trace 'SPY' | 0.3137228895 | 0.3137228895 | 0 | 1.000e-12 | PASS |

Month-end adjusted closes used (last trading day of each month; Yahoo adjusted close, USD):

| Month end | SPY | EFA | EEM | IEF | LQD | GLD | BIL |
|---|---:|---:|---:|---:|---:|---:|---:|
| 2022-11-30 | 387.0740 (11-30) | 59.7510 (11-30) | 35.9628 (11-30) | 85.1525 (11-30) | 90.7553 (11-30) | 164.8100 (11-30) | 77.1392 (11-30) |
| 2022-12-31 | 364.7676 (12-30) | 58.6677 (12-30) | 35.0143 (12-30) | 83.8853 (12-30) | 89.3476 (12-30) | 169.6400 (12-30) | 77.4189 (12-30) |
| 2025-11-30 | 676.0958 (11-28) | 92.0393 (11-28) | 53.2767 (11-28) | 94.0458 (11-28) | 107.1636 (11-28) | 387.8800 (11-28) | 88.7134 (11-28) |

Full SLSQP solution for the last rebalance: SPY 31.3724%, EFA 18.5843%, EEM 5.0433%, IEF 20.0000%, LQD 0.0000%, GLD 10.0000%, BIL 15.0000%.

## How to read this

- Stage 1 proves the parsed raw provider file and the normalized cache are the same numbers.
- The middle stages prove the pipeline formula: returns are recomputed from month-end prices, net returns are replayed from stored weights with 10bp per dollar traded, and the optimizer is checked against a second solver.
- SQL stages prove SQL Server stores the same value and that a recompute in T-SQL lands on it.
- Dash stages call the real callback functions (`portfolio_view`, `fund_view`) and read the rendered value: the KPI card text, the grid cell and the bar height.
- NOT RUN means `MULTI_ASSET_SQLSERVER_URL` was not set when the report was generated.

Prices quoted above are a handful of illustrative observations from the provider; see `docs/data_usage_register.md`.
