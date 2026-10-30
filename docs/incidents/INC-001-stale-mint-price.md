# INC-001 — Stale MINT adjusted close propagates into fund analytics

**Status:** Simulated and reproduced on this machine 2026-10-30. **This is not a real production event.** No provider delivery actually froze; the fault was injected into a throwaway copy of the real cache to test whether the pipeline could detect it. It could not, and now it can.

| Field | Value |
|---|---|
| Incident class | Silent data-quality fault — repeated (frozen) price observations |
| Instrument | `MINT` (PIMCO Enhanced Short Maturity Active ETF, one of the two active funds) |
| Fault window | 2025-11-17 to 2025-11-28, 9 trading days, close frozen at `96.82756042480467` (the 2025-11-14 value) |
| Detected by | Manual inspection only, before the fix |
| Detected by | `multi_asset.data.check_unchanged_runs`, after the fix |
| Owner | Research maintainer (`Lifewitdata`), who also acts as market-data owner for this repository |
| Consumer blast radius | 1 fund row, 2 rolling rows, 4 factor rows, 1 rate-sensitivity row, 2 monthly returns; 0 portfolio rows materially |

## What went wrong

The pipeline accepted a price history in which MINT stopped moving for nine consecutive trading days and published analytics computed from it. Nothing raised.

## Root cause

The pre-existing ingestion checks validate *presence*, *shape* and *timing*. They do not validate *change*:

| Check that existed | Why it passed on frozen data |
|---|---|
| Cache SHA-256 matches `data/raw/manifest.json` | The manifest records what the provider delivered. A frozen series that really arrived frozen hashes correctly. |
| No duplicate `(date, ticker)` keys | Repeats are on different dates, so keys stay unique. |
| Every ticker present on every trading day (full cross-section) | The rows exist; only their values are stale. |
| Prices finite and positive, no forward filling | A repeated positive price is finite and positive. |
| Month-end observation no more than 7 days before the calendar month end | 2025-11-28 is 2 days before 2025-11-30. |
| Returns are not NaN | A zero return is a legitimate value, not a missing one. |

Forward filling was already banned, which is why the fault is not a fabricated row — it is a *real row whose value should have moved and did not*. That is a different failure mode and the existing guardrails had no view of it.

## Reproduction

The numbers below were produced on Windows 11 with Python 3.11.16. From the repository root, in PowerShell:

```powershell
$env:PYTHONPATH = "src"
$env:PYTHONIOENCODING = "utf-8"
& "C:\Users\hp\portfolio-env\Scripts\python.exe" scripts\stale_price_incident.py
```

The script copies `data/raw/` twice into temporary directories — a control copy and an injected copy — rewrites the injected `prices.csv` and its manifest checksum, then runs the full pipeline on both and reconciles all 15 output tables cell by cell. It writes `reports/incidents/stale_price_scope.csv`, `stale_price_changed_cells.csv` and `stale_price_simulation.json`. Nothing under `data/` or `data/processed/` is touched.

Old check versus new check, on the same injected file:

```text
checks_before_fix : PASS  checksums, duplicate keys, full cross-section,
                          positive finite prices, month-end gap <= 7 days
check_after_fix   : REJECTED  Possible stale feed: MINT close 96.82756042480467
                          repeated for 9 trading days (2025-11-17 to 2025-11-28);
                          1 run(s) over limit. See docs/incidents/
```

The rejection comes from `unchanged_runs()` plus `check_unchanged_runs()` in [src/multi_asset/data.py](file:///C:/Users/hp/Documents/Qoder/2026-10-30/3b436995/repo/src/multi_asset/data.py), called at the end of `validate_prices()`. Limits live in [src/multi_asset/config.py](file:///C:/Users/hp/Documents/Qoder/2026-10-30/3b436995/repo/src/multi_asset/config.py): `STALE_RUN_DAYS = 5`, `STALE_RUN_OVERRIDES = {"BIL": 15}`.

The per-ticker limit is not arbitrary. Measured longest unchanged runs in the real 2013-2025 cache:

| Ticker | Longest unchanged run | Classed |
|---|---:|---|
| BIL | 10 (2015-10-06 to 2015-10-19 and 2016-08-04 to 2016-08-17) | genuine — a T-bill ETF whose adjusted close legitimately repeats |
| MINT | 3 | genuine |
| AGG, BOND, IEF | 2 | genuine |
| EEM, EFA, GLD, LQD, SPY | 1 | genuine |

BIL is the only ticker that legitimately exceeds 5, so it alone gets a 15-day allowance. The other nine fit under the default. Three unit tests in [tests/test_data.py](file:///C:/Users/hp/Documents/Qoder/2026-10-30/3b436995/repo/tests/test_data.py) pin the behaviour: a 9-day MINT freeze is rejected, a 5-day MINT freeze is allowed, a 10-day BIL run is allowed and a whole-August-2016 BIL freeze is rejected.

## SQL Server diagnostics

[sql/03_stale_price_diagnostics.sql](file:///C:/Users/hp/Documents/Qoder/2026-10-30/3b436995/repo/sql/03_stale_price_diagnostics.sql) is read-only and uses `LAG` plus a gaps-and-islands grouping to find repeat runs in `research.daily_prices`, with the same limits hard-coded so T-SQL and Python agree.

Run against the clean `MultiAssetResearch` database, query 1 returns 22 rows, all BIL and all `within limit`, and queries 2 and 3 return nothing. Run against `MultiAssetResearch_Verify` after the same fault was applied in T-SQL:

```text
frozen_rows
-----------
          9

-- query 1 (repeat runs)
ticker|first_repeat|last_repeat|repeated_days|limit_days|repeated_close       |status
MINT  |2025-11-17  |2025-11-28 |9            |5         |96.827560424804673   |STALE
BIL   |2015-10-06  |2015-10-19 |10           |15        |72.762916564941406   |within limit
... 22 further BIL rows, all within limit

-- query 2 (did peers move?)
ticker|first_repeat|last_repeat|repeated_days|days_with_other_moves|other_tickers_moving
MINT  |2025-11-17  |2025-11-28 |9            |9                    |9

-- query 3 (affected downstream scope)
affected_table     |series|affected_rows|first_date|last_date
fund_metrics       |MINT  |1            |NULL      |NULL
monthly_returns    |MINT  |2            |2025-11-30|2025-12-31
rolling_fund_metrics|MINT |2            |2025-11-30|2025-12-31
```

Query 2 is the discriminator: on all 9 stale days the other nine tickers moved. A ticker that repeats while the rest of the cross-section is flat is plausibly real; a ticker that repeats while all nine peers move is a feed fault.

## Scope

Cell-level diff, control run versus injected run, materiality threshold `1e-8`:

| Table | Rows | Rows changed | Materially changed | Columns affected | Max abs difference |
|---|---:|---:|---:|---|---:|
| daily_prices | 30,390 | 9 | 9 | `adjusted_close` | 1.542e-01 |
| monthly_prices | 145 | 1 | 1 | `MINT` | 1.542e-01 |
| monthly_returns | 144 | 2 | 2 | `MINT` | 1.599e-03 |
| fund_metrics | 2 | 1 | 1 | `tracking_error`, `information_ratio`, `annual_mean_active_return`, `annual_volatility`, `sharpe_cash_proxy`, `active_month_hit_rate` | 6.944e-03 |
| rolling_fund_metrics | 218 | 2 | 2 | same six plus `cagr` | 2.034e-01 |
| factor_coefficients | 8 | 4 | 4 | `coefficient`, `pvalue_hac`, `ci_low`, `ci_high`, `r_squared` | 1.175e-02 |
| rate_sensitivity | 4 | 1 | 1 | `return_per_1pp_yield_change`, `pvalue_hac`, `r_squared` | 2.104e-02 |
| portfolio_returns | 648 | 117 | 0 | — | 6.279e-10 |
| weights | 4,536 | 299 | 0 | — | 3.600e-10 |
| portfolio_metrics | 6 | 3 | 0 | — | 2.372e-10 |
| assets, daily_macro, monthly_macro, volatility_scores, volatility_predictions | — | 0 | 0 | — | ≤1.041e-16 |

The three portfolio tables move, but not because MINT is an input. The optimized portfolios hold only the 7 investable ETFs and their price columns are bitwise identical between runs. A control run — clean copy against committed outputs, with no fault injected — reproduces the same magnitude of movement, so the difference is solver and floating-point non-determinism in CVXPY/CLARABEL, not incident impact. Classifying them as noise is the honest reading; classifying them as *unaffected* would be wrong, because they are not bit-for-bit reproducible.

## Impact on published numbers

| Measure | Clean | Stale | Change |
|---|---:|---:|---:|
| MINT return, 2025-11 | 0.3389% | 0.1794% | -0.160 pp |
| MINT return, 2025-12 | 0.4190% | 0.5789% | +0.160 pp |
| MINT tracking error vs BIL (full sample) | 1.1727% | 1.1749% | +0.0022 pp |
| MINT information ratio | 0.4967 | 0.4958 | -0.0009 |
| MINT annual mean active return | 0.58245% | 0.58248% | +0.00003 pp |
| MINT active-month hit rate | 77.08% | 76.39% | -0.70 pp |
| MINT 36m Sharpe (cash proxy), 2025-11 window | 1.873 | 1.670 | -0.203 |
| MINT treasury-excess factor p-value | 0.1135 | 0.1253 | +0.0118 |

Nine frozen days inside one 144-month sample barely move the full-sample statistics — the information ratio shifts in the fourth decimal. They move a rolling 36-month window much more (0.20 on Sharpe) because the frozen month is at the live edge of the window, and they flip two months of active return into the wrong sizes. A client reading the latest rolling card is the one exposed, not a client reading the headline.

## Escalation

| Step | Owner | Trigger |
|---|---|---|
| Stop the load | Research maintainer | `check_unchanged_runs` raises during `load()` or `fetch()` — the pipeline already halts before writing outputs |
| Confirm against a second view | Research maintainer (market-data owner) | re-request the same ticker/period from the Yahoo chart endpoint and compare; a repeat is only a fault if the provider now returns different values |
| Notify downstream readers | Research maintainer | anyone holding a generated brief, screenshot or dashboard built from the affected run |
| External escalation | Not applicable | this repository has no provider support contract or data-vendor ticket queue; escalation is internal |

No external escalation contact, SLA or on-call rota exists for this project, and none is claimed here.

## Plain-English response for a reader of the dashboard

> One of the funds we track, MINT, briefly stopped updating in our price feed. For nine trading days in late November 2025 it showed exactly the same price as November 14, while every other holding moved normally. Our loader did not catch that at the time; it now does and will refuse to publish until the data is refreshed.
>
> What it changed: MINT's reported return for November was too low and for December too high, by about six one-hundredths of a percentage point each, and the most recent three-year risk-adjusted figures for that one fund were overstated. Nothing else changed. The model portfolios are built from seven index ETFs, none of which were affected, and their weights and returns are unchanged.
>
> What we did: added an automatic check that rejects any fund or ETF whose price repeats for longer than that instrument ever legitimately does, so this cannot silently reach a report again. Refreshed the data, rebuilt the numbers, and re-verified them against the stored database.

## Remediation

1. `check_unchanged_runs` now runs inside `validate_prices`, so both `load()` and `fetch()` reject a stale cache before any output is written.
2. Recovery procedure: `python -m multi_asset.pipeline --download` (re-fetch), then `python -m multi_asset.pipeline` (rebuild processed files and `data_quality.json`), then `python -m multi_asset.database` (transactional reload; it rolls back unless every table count and every cell reconciles), then `python -m multi_asset.reconcile` and `python -m multi_asset.evidence`.
3. `sql/03_stale_price_diagnostics.sql` is kept for read-only auditing of a database that is already loaded, for the case where a fault entered before the Python check existed.

## Known limits of this fix

- The check compares consecutive trading days only. A feed that returns a *plausible but wrong* value each day is not caught by it; that needs a peer or NAV cross-check.
- The 5-day default is calibrated on 2013-2025 data for these ten tickers. A new instrument inherits the default and may need its own override.
- Weekend and holiday gaps are not runs; `validate_prices` already requires the full daily cross-section, so a missing day is rejected separately and earlier.
- A genuinely flat market can produce a repeat run. The peer-movement query in `sql/03` is what distinguishes the two, and the Python check is deliberately conservative: it rejects and asks for a re-fetch rather than silently trusting the longer run.
