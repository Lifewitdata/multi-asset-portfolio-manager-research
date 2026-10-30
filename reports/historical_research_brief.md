# Historical portfolio research brief

Study: 2014-01-31 to 2025-12-31; 108 holding months after the training window.

## Client allocation comparison

Net returns include modelled trading costs. Each optimized profile has its own equity-matched policy comparator.

- Balanced Optimized: CAGR 7.42%, volatility 8.88%, maximum drawdown -21.24%.
- Balanced Policy: CAGR 8.51%, volatility 9.50%, maximum drawdown -20.51%.
- Conservative Optimized: CAGR 5.10%, volatility 6.28%, maximum drawdown -18.64%.
- Conservative Policy: CAGR 5.25%, volatility 7.07%, maximum drawdown -18.25%.
- Growth Optimized: CAGR 9.29%, volatility 11.91%, maximum drawdown -25.16%.
- Growth Policy: CAGR 11.17%, volatility 12.19%, maximum drawdown -22.52%.

## Active fund evaluation

These are fund-level market-price comparisons. Benchmark proxies are not official indexes or manager-tenure attribution.

- BOND versus AGG: annual tracking error 1.78%, information ratio 0.27, annual mean active return 0.48%; annual OLS alpha 0.47% (HAC p-value 0.264).
- MINT versus BIL: annual tracking error 1.17%, information ratio 0.50, annual mean active return 0.58%; alpha/beta not identified because the comparator is also the cash proxy.

## Forecast validation

Lowest walk-forward MAE: Random forest; 97 forecast months. The model is not used to trade the portfolios.

- Random forest: MAE 0.0559; RMSE 0.1005 in annualized volatility decimal units.
- OLS: MAE 0.0605; RMSE 0.1096 in annualized volatility decimal units.
- Persistence: MAE 0.0667; RMSE 0.1158 in annualized volatility decimal units.
- Trailing mean: MAE 0.0678; RMSE 0.1162 in annualized volatility decimal units.

## Interpretation and next research

Compare volatility and drawdown against the relevant policy before treating higher returns as improvement. Investigate factor exposures and benchmark mismatch before attributing active return to skill. Test different cost and training-window assumptions before selecting a portfolio.

## Limits

Retrospectively selected surviving ETFs; adjusted prices can be revised. USD unhedged market-price total-return proxies, not official NAV returns. No taxes, bid/ask spreads, currency hedging or intramonth drawdowns. Trading at observed month-end prices is idealized. Profiles are illustrative, not client advice. Current FRED history is not a vintage database. Credit factor is not duration-neutral. No individual manager attribution or future-performance claim.
