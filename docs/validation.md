# Validation record

Two environments are recorded separately. Nothing here claims a check ran where it did not.

## Linux, Python 3.12 — 30 October 2026

Validated on October 30, 2026, in a Linux Python 3.12 environment. These are observed checks, not claims about an untested Windows installation.

| Check | Result |
|---|---|
| Yahoo historical downloads | 10 instruments, 30,390 adjusted-close observations |
| FRED Treasury yield downloads | DGS10/DGS2, 6,042 nonmissing observations |
| Monthly return coverage | 144 months per instrument; no duplicates or missing month-end prices |
| Allocation backtest | 108 holding months × 6 portfolios; 4,536 target-weight rows |
| Forecast validation | 97 holdout months × 4 models |
| Automated unit / callback suite | **53 passed, no warnings** |
| Notebook execution | **12 code cells executed**, 24 captured outputs via in-process IPython |
| Real Chromium browser | Profile and fund changes, custom allocation calculation, desktop/mobile layout; no JavaScript errors |
| SQL Server statement generation | Tested for locked upsert construction and safe identifiers |
| Live SQL Server / ODBC execution | **Not run in this environment; verify on Windows** |
| AI evidence validation | Correct typed facts accepted; changed values/types, missing/duplicate/unknown keys rejected |
| Actual external AI response / API | **Not run**; workflow is manual and requires human explanation review |

The normal Jupyter kernel launcher was blocked by this environment's socket restrictions. The same notebook was then executed through `scripts/execute_notebook_inprocess.py`, with outputs captured to `reports/local/executed_research.ipynb`. The normal executor remains available for Windows and GitHub Actions; this record does not claim it succeeded locally.

The first dependency combination produced third-party deprecation warnings. The final environment uses NumPy below 2.4 with pandas 2.x, current AG Grid tables instead of deprecated Dash DataTable, and disables Dash's unused pytest browser plugin. The final test run had no warnings. `requirements-tested-linux-py312.txt` records the environment; it is not a portable Windows lock file.

Browser tests are optional: install Playwright, install Chromium, then run `python scripts/browser_smoke.py` after generating the historical outputs. The script starts its own temporary local server and checks actual rendered callbacks. Screenshots are in `docs/screenshots/`.

## Windows 11, Python 3.11.16, SQL Server 2025 Developer — 30 October 2026

Machine: Windows 10.0.26300, x64, 7.5 GB RAM. Interpreter `C:\Users\hp\portfolio-env\Scripts\python.exe` (3.11.16). Instance `localhost`, Windows authentication, ODBC Driver 18. All times UTC.

| Check | Result |
|---|---|
| Offline pipeline from the validated cache | Ran. 10 instruments, 30,390 daily rows, 144 return months, 108 holding months, 97 forecast months, best volatility model by MAE: Random Forest |
| Automated suite | **109 passed** in 13.6 s |
| Loader into `MultiAssetResearch` (11:11 UTC build) | 12 tables: 10 / 30,390 / 6,042 / 144 / 648 / 4,536 / 6 / 2 / 218 / 8 / 4 / 4 rows |
| Repeat load, same database | Second transcript byte-identical to the first: same counts, no duplicates |
| Fresh load into a scratch database | `MultiAssetResearch_Verify` created from nothing at 17:01 UTC; the loader ran `sql/01_schema.sql`, staged, merged and reported the same 12 counts |
| Column-level reconciliation, clean | **PASS — 49,756 cells, 0 mismatches** at 1e-12 (`reports/reconciliation/summary.json`, target `MultiAssetResearch_Verify@localhost`) |
| Column-level reconciliation, faults injected | `python scripts/injected_fault_demo.py` **caught all 3**: a one-part-per-billion edit to one MINT close, a deleted Growth Optimized GLD weight row, 0.01 added to BOND tracking error. Transaction rolled back; the database was unchanged afterwards |
| `sql/02_analytics.sql` | Table counts 30,390 / 144 / 648 / 4,536; **0 rows** breaching the fully-invested long-only weight check; **0 rows** with `training_end >= date`; 582 rolling 12-month returns; 2 fund rows |
| Source-to-screen evidence | **23 of 23 stages PASS** at 17:07 UTC (`reports/calculation_evidence.md`), including the T-SQL recomputes and both Dash modes |
| Dash CSV mode vs SQL Server mode | Same rendered values: KPI card 7.42%, fund grid tracking error 0.01783, allocation bar SPY 0.3137228895. This is the evidence report calling `portfolio_view` / `fund_view` in each mode, not a visual guess |
| Stale-feed diagnostics, clean data | `sql/03_stale_price_diagnostics.sql`: 22 repeat runs of 5 days or longer, **all BIL and all within limit**, 0 STALE; the peer-movement and scope queries returned nothing |
| Stale-feed diagnostics, injected data | Same script on `MultiAssetResearch_Verify` after freezing 9 MINT closes in T-SQL: **1 STALE row** (MINT 2025-11-17 to 2025-11-28, limit 5), 9 of 9 stale days with all 9 peers moving, and 3 scope rows (1 `fund_metrics`, 2 `monthly_returns`, 2 `rolling_fund_metrics` for MINT) |
| Stale-fault pipeline simulation | `python scripts/stale_price_incident.py`: the pre-existing checks **passed** the frozen series, the new check rejected it, and 7 tables changed materially while 3 moved only by solver noise. See [INC-001](incidents/INC-001-stale-mint-price.md) |
| Notebook | `python scripts/execute_notebook.py` executed **12 code cells** with a real ipykernel and wrote `reports/local/executed_research.ipynb`. The in-process fallback was not needed on Windows |
| AI field-mapping review check | `python scripts/check_field_mapping.py`: 10 proposals, 3 accepted, 6 corrected, 1 field absent from the catalog |
| Real external AI response / API | **Not run.** No key configured, no call made |
| Chromium smoke test | **Not run on this machine.** Playwright is not installed in `portfolio-env` |

### A defect this pass found and fixed

`portfolio_metrics.alpha_pvalue_hac` for the three static Policy portfolios was published as a probability even though a Policy portfolio is by construction identical to its own comparator. The pre-fix values were Balanced 0.00867, Conservative 0.01671 and Growth 3.66e-07 — the last one implying startlingly significant alpha against a benchmark that cannot differ from it. The intercept is floating-point noise, and its HAC standard error is near zero.

`analytics.evaluate_funds` now nulls the alpha p-value whenever tracking error is at or below 1e-12, `tests/test_research.py::test_identical_benchmark_zero_te` asserts the null plus `|alpha| < 1e-12` and `beta = 1`, and the pipeline was rerun. The Optimized rows are unchanged to 15 significant figures, and the aggregate figures quoted in `reports/historical_research_brief.md` do not change.

Because the processed CSV changed, the maintainer's `MultiAssetResearch` database no longer matches them until it is reloaded — the loader would roll that reload back rather than let the difference stand, which is why the two committed evidence artifacts above were regenerated against the scratch database built from the current CSVs. Run `python -m multi_asset.database` against `MultiAssetResearch` to bring it in line.

### Windows notes

- Low free memory (about 0.9 GB available during the run) made one `MERGE` wait 12 minutes on a `RESOURCE_SEMAPHORE` grant for 35 MB. Nothing failed; the statement completed. On a busy machine expect SQL loads to be slow rather than broken.
- `sqlcmd` is at `C:\Program Files\Microsoft SQL Server\Client SDK\ODBC\180\Tools\Binn\sqlcmd.exe` and needs `-S localhost -E -C` for this instance.
- `PYTHONIOENCODING=utf-8` is required for the report scripts, which print the `×` and `–` characters, and `OPENBLAS_NUM_THREADS=1` keeps the optimizer stages from thrashing.
- Line endings are pinned by `.gitattributes`. Processed-file hashes are byte hashes, so CRLF drift between clones would look like edited data to `verify_processed`.

## Reproduce

```bash
python -m pip install -e ".[dev]"
python -m multi_asset.pipeline --download
python -m pytest -q
python scripts/execute_notebook.py
```

With SQL Server configured (`MULTI_ASSET_SQLSERVER_URL`, see [windows_setup.md](windows_setup.md)):

```bash
python -m multi_asset.database
python -m multi_asset.reconcile --output reports/reconciliation
python -m multi_asset.evidence
python scripts/injected_fault_demo.py
python scripts/stale_price_incident.py
sqlcmd -S localhost -E -C -i sql/03_stale_price_diagnostics.sql
```

`--download` can receive revised provider histories. To reproduce the exact local source snapshot, retain the original ignored cache and use `python -m multi_asset.pipeline` without downloading.

## Not verified

- A real external AI-generated JSON response fed to `multi_asset.ai_brief`. The validator is unit-tested against hand-written responses only.
- Rendered browser behaviour on this machine (no Playwright). The Chromium result above is from the Linux run.
- GitHub Actions for the files added in this pass; CI runs on push, and nothing here has been pushed.
- Provider terms beyond what [data_usage_register.md](data_usage_register.md) quotes; several items there are still listed as unknown.
- Anything after December 2025. The study period is fixed.
