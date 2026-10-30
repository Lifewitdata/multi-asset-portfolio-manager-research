# Windows 11 setup: Python 3.11, SQL Server and Dash

Use this repository's own short environment path. Your existing ABS environment and database can remain in place.

## 1. Download and open the project

Download the repository ZIP and extract it to a short folder, for example `C:\Users\hp\Projects\multi-asset-research`. Open PowerShell in the folder containing `pyproject.toml`. Do not run inside the ZIP preview.

Create the environment using the Python installation already used for ABS:

```powershell
py -V:Astral/CPython3.11.16 -m venv "C:\Users\hp\portfolio-env"
& "C:\Users\hp\portfolio-env\Scripts\python.exe" -m pip install -e ".[dev,sqlserver]"
```

If that Python selector is no longer present, use `py --list-paths` and select an installed Python 3.11/3.12. Keeping the environment outside the long ZIP folder avoids the previous Windows path-length error. An editable install must remain in its source folder; reinstall if you move the project.

## 2. Download actual history and build outputs

```powershell
& "C:\Users\hp\portfolio-env\Scripts\python.exe" -m multi_asset.pipeline --download
```

Expected fixed-period counts: 10 instruments, 30,390 daily price rows in the recorded run, 144 return months and 108 portfolio backtest months. Sources can revise histories; consult `reports/local/data_quality.json` rather than silently accepting changed counts. The model comparison records 97 forecast months. If a source fails, retry later; never replace it with fabricated data.

Run offline from the validated cache afterward:

```powershell
& "C:\Users\hp\portfolio-env\Scripts\python.exe" -m multi_asset.pipeline
& "C:\Users\hp\portfolio-env\Scripts\python.exe" -m pytest -q
```

## 3. Start the dashboard

```powershell
& "C:\Users\hp\portfolio-env\Scripts\python.exe" -m multi_asset.dashboard
```

Open `http://127.0.0.1:8051`. Keep this terminal running. Use a second PowerShell window for the following steps, or press Ctrl+C before entering another command. The dashboard is a local development application, not a public hosted service.

Check all three profiles, both active funds, and the allocation sliders. Growth has an 80% equity budget; Conservative has 25%. A 10% equity budget with a 30% single-asset cap is deliberately infeasible; the sandbox should show a clear message.

## 4. Create a separate SQL Server database

In SSMS, use your existing `localhost` Windows-authenticated connection. Run:

```sql
IF DB_ID(N'MultiAssetResearch') IS NULL
    CREATE DATABASE MultiAssetResearch;
GO
USE MultiAssetResearch;
GO
SELECT DB_NAME() AS CurrentDatabase;
```

This is Microsoft SQL Server, not MySQL. ODBC Driver 18 for SQL Server is required, as in the ABS project.

In a PowerShell window in this project folder:

```powershell
$env:MULTI_ASSET_SQLSERVER_URL = "mssql+pyodbc://@localhost/MultiAssetResearch?driver=ODBC+Driver+18+for+SQL+Server&trusted_connection=yes&Encrypt=yes&TrustServerCertificate=yes"
& "C:\Users\hp\portfolio-env\Scripts\python.exe" -m multi_asset.database
```

`TrustServerCertificate=yes` is for the local development instance's self-signed certificate. Use a trusted certificate for a deployed server. The loader creates schema/tables, stages data, merges by primary keys and checks exact counts before committing. It does not truncate or delete tables. Existing surplus rows cause rollback; inspect them rather than deleting data blindly. Use a separate database for a different study configuration.

Run the loader a second time to confirm idempotence. Both runs must report the same counts. Then run `sql/02_analytics.sql` in the current `MultiAssetResearch` connection. The weight and look-ahead checks should return **no rows**.

| Table | Recorded row count |
|---|---:|
| assets | 10 |
| daily_prices | 30,390 |
| daily_macro | 6,042 |
| monthly_returns | 144 |
| portfolio_returns | 648 |
| weights | 4,536 |
| portfolio_metrics | 6 |
| fund_metrics | 2 |
| rolling_fund_metrics | 218 |
| factor_coefficients | 8 |
| rate_sensitivity | 4 |
| volatility_scores | 4 |

## 5. Use SQL Server as the dashboard source

Stop the dashboard, then in a terminal where the connection variable is set:

```powershell
$env:MULTI_ASSET_DASH_SOURCE = "sqlserver"
& "C:\Users\hp\portfolio-env\Scripts\python.exe" -m multi_asset.dashboard
```

The banner must say `Source mode: SQLSERVER`. SQL tables are read on startup; restart after refreshing. To use CSVs again:

```powershell
$env:MULTI_ASSET_DASH_SOURCE = "csv"
```

## 6. Notebook and report

```powershell
& "C:\Users\hp\portfolio-env\Scripts\python.exe" scripts\execute_notebook.py
notepad .\reports\local\executive_summary.md
```

The notebook executor writes `reports/local/executed_research.ipynb`. Open it in VS Code with the Jupyter extension or JupyterLab. If an environment prevents kernel sockets, `scripts/execute_notebook_inprocess.py` executes the same cells through IPython and captures outputs; it is an explicitly documented fallback.

## 7. Manual AI-assisted research review

```powershell
& "C:\Users\hp\portfolio-env\Scripts\python.exe" -m multi_asset.ai_brief
notepad .\reports\local\ai_prompt.txt
```

Paste the prompt into your AI tool. Save only its JSON response as `reports/local/ai_response.json`, then run:

```powershell
& "C:\Users\hp\portfolio-env\Scripts\python.exe" -m multi_asset.ai_brief --response reports/local/ai_response.json
```

Passing validates exact facts and types. You must still read the explanations for unsupported conclusions. No AI API key or API integration is required or claimed.

## 8. Maintenance

`scripts/refresh.ps1` runs cached research and optionally downloads data and/or loads SQL. Example:

```powershell
.\scripts\refresh.ps1 -Python "C:\Users\hp\portfolio-env\Scripts\python.exe" -LoadSql
```

The script appends a local transcript and checks process exit codes. It does not register a Windows scheduled task automatically. If you later schedule it, set the working directory and connection environment for that task account. The study end remains fixed at December 2025; `-Download` refreshes provider revisions, not the study period.

Back up the raw cache and manifest to preserve a particular research run. Never commit `.env`, credentials, raw provider data or full downloaded histories to the public repository.
