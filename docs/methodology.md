# Research methodology

## Dataset and return construction

Download daily adjusted close for SPY, EFA, EEM, IEF, LQD, GLD, BIL, AGG, BOND and MINT. The download starts in December 2013 to supply the first month-end base value. The study ends on December 31, 2025; it deliberately excludes incomplete and later months.

Dates are converted from provider timestamps using the exchange timezone. All instruments must be USD-denominated. Each trading date must contain the entire instrument cross-section. Keys must be unique, prices finite/positive and month-end coverage complete. A last observation more than seven calendar days before month end is rejected. Monthly return is P_t / P_(t-1) − 1, without forward filling. If the provider omits a trading day for every ticker, cross-sectional coverage alone cannot detect that omission; source and exchange-calendar reconciliation is a future improvement.

Adjusted market prices reflect distributions/splits and fund-level expenses; they are total-return proxies, not NAV total returns. They do not include investor taxes or trading frictions. All foreign-equity exposures remain unhedged in USD.

## Portfolios and constraints

The investable set is SPY/EFA/EEM/IEF/LQD/GLD/BIL. AGG is the core-bond comparator; BOND/MINT are evaluation subjects, not allocation inputs. Profiles set aggregate equity weights to 25%, 55% and 80% respectively. Long-only weights sum to one. Single instruments are capped at 50%, gold at 10%, bills at 15%.

For holding month t, use monthly returns t−36 through t−1 to estimate Ledoit–Wolf shrinkage covariance and minimize w'Σw with CVXPY/CLARABEL. No expected-return estimate or forecast enters this optimization. Infeasible or nonoptimal solutions raise errors, not silent fallback allocations.

Each profile has a policy with the same equity budget: 60/25/15 within equities, 5% gold, 5% bills, and a 70/30 split of the remaining weight between Treasuries and investment-grade credit. Policies are transparent illustrative rules, not external published indexes.

## Timing and trading costs

Monthly rebalancing uses the end of the previous month as the decision point. For each holding month, portfolio gross return is target weights dotted with asset returns. Previous holdings drift with asset returns before the next trade. The first allocation starts from uninvested cash and incurs a full initial purchase cost.

Traded fraction = sum(abs(target_weight − drifted_weight)). Cost = traded fraction × 10 / 10,000. This charges both buys and sells; a complete rotation costs 20bp. Net return = (1 − cost) × (1 + gross_return) − 1. Monthly fees are deducted before the holding-period return. This is an idealized proportional-cost rebalance; exact self-financing settlement, spreads, slippage, taxes and market impact are not modelled.

The first 36 months train the model. All six series share January 2017–December 2025 holding dates. Optimization uses only information dated before each holding month, but retrospective instrument selection, revised histories and assumed execution prices still limit realism.

## Performance and fund evaluation

CAGR = product(1+r)^(12/n) − 1. Annual volatility uses sample standard deviation × √12. Drawdown includes initial wealth of one so a loss in the first holding month is counted. Tracking error is annualized standard deviation of arithmetic active returns. Information ratio = mean(active return) × 12 / tracking error. Undefined ratios remain missing.

The reported cash-proxy Sharpe divides annual mean return above BIL by total-return volatility. BIL is an investable bill ETF, not an exact risk-free rate. Annual mean active return is an arithmetic mean × 12, not CAGR difference.

BOND/AGG and MINT/BIL are investable fund comparisons over January 2014–December 2025. Rolling windows are exactly 36 months. Comparators are not official fund benchmark indexes. Holdings, credit quality and duration can differ, especially for MINT versus Treasury bills.

OLS regresses fund excess returns over BIL on comparator excess returns. Annual alpha is 12 times the monthly intercept, with HAC standard errors using three lags. If comparator excess returns have no variation (MINT/BIL), Jensen alpha, beta and alpha p-value are undefined. Raw mean active return and tracking error remain valid. No individual-manager skill claim is made.

## Factors and rates

Fund excess returns are contemporaneously regressed on SPY−BIL, IEF−BIL and LQD−IEF. Coefficient intervals use HAC inference. These are ETF factors, not academic Fama–French factors. LQD−IEF is a credit-relative proxy with residual duration and other risks; it is not a pure credit spread factor. Coefficients describe association, not causality.

A separate regression relates monthly fund excess returns to month-end changes in DGS10. The coefficient is return per **one percentage-point** yield change, not a formally estimated bond duration. DGS2 and DGS10 are retained for yield-curve exploration. Macro history is the current downloaded vintage and never enters allocation or forecasting.

## Volatility prediction

The SPY target is monthly sample standard deviation of daily log returns × √252, requiring at least 15 daily returns per target month. Features for month t use volatility at t−1, means of t−1 through t−3 and t−1 through t−12, and absolute month t−1 return. Expanding training starts with 36 complete feature rows; predictions use only earlier target labels.

Compare persistence, three-month trailing mean, linear regression and Random Forest (100 trees, depth 3, minimum leaf size 6, seed 42). Parameters are fixed, with no shuffled validation or test-set tuning. Predictions are floored at zero. MAE and RMSE use annualized-volatility decimal units. Report both scores; test performance is descriptive, not a statistically established durable model advantage.

## Reproducibility, AI and scope

Every raw payload and normalized file is hashed. Processed-file hashes are checked before CSV dashboard startup and SQL loading. A failed or partial download never substitutes synthetic data. Data revisions can change a future refreshed run; retain your local cache to reproduce a particular run.

The AI module creates a prompt from computed facts and validates externally supplied JSON for exact keys, types and values. It cannot verify the truth of free-text explanations; human review is mandatory. No API call is implemented or claimed.

This project demonstrates quantitative research methods. It does not establish two years of professional experience, production readiness, real client suitability, manager-tenure attribution, or large-scale performance.
