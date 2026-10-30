# Data usage register

Last reviewed: **2026-10-30** by the research maintainer. This register records what each source is used for, what is held where, what the provider's published terms say, and what is still **unknown**. It does not grant or assume any permission. No written licence, API agreement or permission letter is held for any source below.

Quotes are short excerpts taken from the linked pages on 2026-10-30. Terms change; re-read the page before relying on an excerpt.

## Register

| | Yahoo Finance chart endpoint | FRED graph CSV (DGS10, DGS2) | Fund issuer web pages |
|---|---|---|---|
| **What is used** | Daily adjusted close for SPY, EFA, EEM, IEF, LQD, GLD, BIL, AGG, BOND, MINT, 2013-12-02 to 2025-12-31 | Daily 10-year and 2-year Treasury constant-maturity yields, percent | Fund names and strategy descriptions, used as links only. No numbers are taken from them |
| **Access method** | `query1.finance.yahoo.com/v8/finance/chart/<ticker>` (an unofficial, undocumented endpoint), called by `data.fetch()` with no API key | `fred.stlouisfed.org/graph/fredgraph.csv?id=<series>`, called by `data.fetch()` with no API key. The keyed FRED API is not used | Manual browsing |
| **Held locally (not in Git)** | Raw JSON payloads and `data/raw/prices.csv` (30,390 rows); every processed table under `data/processed/`; full daily history in the local SQL Server database `research.daily_prices` | `data/raw/fred_*.csv`, `data/raw/macro.csv`, `research.daily_macro` | Nothing |
| **Committed to Git** | (a) `reports/source_manifest.json`: URLs, hashes and row counts only. (b) Aggregate statistics in `reports/historical_research_brief.md`, `reports/reconciliation/` and the dashboard screenshot. (c) Individual observations: 57 month-end adjusted closes in `reports/calculation_evidence.md`, 10 MINT closes (9 true values plus the frozen 2025-11-14 price) in `reports/incidents/`, and one further MINT close with its deliberately altered copy in `reports/reconciliation/injected_fault_mismatches.csv` (the same 2025-11-28 observation the incident already quotes) — 67 distinct raw closing prices in total. (d) `sql/03_stale_price_diagnostics.sql` quotes no observations | Manifest metadata; regression coefficients in the brief. No yield observations | Links in `docs/data_sources.md` |
| **Published terms (evidence)** | [Yahoo Terms of Service](https://legal.yahoo.com/us/en/yahoo/terms/otos/index.html), effective 6 May 2025. Sec. 2.4 prohibits accessing or collecting data "using any automated means … robots, spiders, scrapers" without permission. Sec. 2.5 prohibits commercial use. Sec. 8.1 says the services are provided "AS-IS" | [FRED legal notices](https://fred.stlouisfed.org/legal/). The general licence is "solely for your personal, non-commercial use". Third-party series require you to "contact the data owner to obtain permission". "Commercial use without the prior written consent of the Bank" is prohibited. [DGS10 series page](https://fred.stlouisfed.org/series/DGS10): source Board of Governors, release H.15, units "Percent, Not Seasonally Adjusted", and "Data in this graph are copyrighted. Please review the copyright information in the series notes before sharing." [H.15 release](https://www.federalreserve.gov/releases/h15/) footnotes: "Source: U.S. Treasury." | Not reviewed |
| **Permission status** | **Not granted.** Automated collection from this endpoint appears to fall within what Sec. 2.4 restricts without permission. None has been requested | **Personal, non-commercial use only**, under FRED's general licence. No commercial consent requested | **Not reviewed** |
| **Explicit unknowns** | Whether any Yahoo API product or licence covers this endpoint. Which upstream exchanges or vendors supply the adjusted closes, and their redistribution terms. Whether quoting 67 individual closes across `reports/` is acceptable. Whether payloads are revised over time: payload hashes changed between the 2026-10-29 and 2026-10-30 retrievals, yet the derived brief was identical | The copyright text in the DGS2 series notes (only the DGS10 page was read). Whether the H.15 / U.S. Treasury origin changes the "third-party series" position. Any attribution wording FRED requires beyond the suggested citation | Issuer website terms for linking or quoting fund descriptions |
| **Required before commercial use, a hosted service or redistribution** | Obtain written permission from Yahoo, or replace this source with a licensed market-data vendor. Remove the quoted closes from public files if the licence does not cover them | Obtain the Bank's written consent for commercial use. Read the DGS2 series notes. Add the suggested FRED citation to any published output | Review each issuer's site terms before quoting more than names |
| **Owner** | Research maintainer | Research maintainer | Research maintainer |

## Rules this repository follows today

- Raw payloads, normalized price and yield tables, and full processed outputs stay out of Git (`.gitignore`: `data/raw/*`, `data/processed/*`, `reports/local/*`).
- Committed material is limited to metadata, aggregate statistics, and the small number of individual observations listed above. They are kept because the calculation evidence and the incident write-up need visible inputs.
- The dashboard runs locally (`127.0.0.1`) and is not a hosted feed.
- Unit tests use labelled synthetic fixtures. Production code has no synthetic fallback.

## Review triggers

Re-review this register before any of the following: deploying the dashboard beyond localhost; sharing the SQL Server database or processed CSVs; adding a source; using results for clients or for commercial work; or once 12 months have passed since the last review date above.
