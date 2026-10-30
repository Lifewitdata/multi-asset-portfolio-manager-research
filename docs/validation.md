# Validation record

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

## Reproduce

```bash
python -m pip install -e ".[dev]"
python -m multi_asset.pipeline --download
python -m pytest -q
python scripts/execute_notebook.py
```

`--download` can receive revised provider histories. To reproduce the exact local source snapshot, retain the original ignored cache and use `python -m multi_asset.pipeline` without downloading.

## Checks to finish on Windows

1. Load into `MultiAssetResearch` using ODBC Driver 18; reconcile all table counts.
2. Repeat the loader and confirm the same counts, with no duplicates.
3. Run `sql/02_analytics.sql`; weight and training-date exception queries should return zero rows.
4. Start Dash with `MULTI_ASSET_DASH_SOURCE=sqlserver` and compare its numbers with CSV mode.
5. Run the 53 tests in the user's Python 3.11 environment.
6. Optionally review a real AI-generated JSON response with the validator; do not treat exact-value validation as explanation verification.
