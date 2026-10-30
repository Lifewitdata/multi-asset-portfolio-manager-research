# AI-assisted field mapping — worked example, reviewed

This records one concrete AI-assisted step in building [field_catalog.csv](file:///C:/Users/hp/Documents/Qoder/2026-10-30/3b436995/repo/docs/field_catalog.csv): drafting the raw-field mapping for the provider payloads. It exists because "I used AI" is not evidence — the draft, the corrections, the machine check and the approval state are.

| Field | Value |
|---|---|
| Draft produced | 2026-10-30, by the Qoder coding assistant working in this repository |
| External LLM API used | No. No provider key was configured or called for this step |
| Review method | Recompute each proposal's verdict from `docs/field_catalog.csv` with `scripts/check_field_mapping.py`, then read the flagged ones against the code |
| Proposals | 10 — 3 accepted, 6 corrected, 1 field the catalog does not hold |
| Machine check | Passing, and asserted in `tests/test_field_mapping.py` |
| Approval status | **Not approved.** Maintainer sign-off is still outstanding; see "Approval" below |

## The prompt

> Map each field of `data/raw/prices.csv` and `data/raw/macro.csv`, plus the derived fields I list, onto the source payload. For every field give: the JSON or CSV path it comes from, the transform, the units, and what happens to missing values. Use the Yahoo chart v8 response shape and the FRED `fredgraph.csv` shape. Do not invent paths that the payload does not contain.

## The draft, verbatim

```json
{
  "review": {
    "draft_by": "Qoder coding assistant (no external LLM API call)",
    "date": "2026-10-30",
    "approval": "pending maintainer sign-off",
    "reference": "docs/field_catalog.csv"
  },
  "proposals": [
    {
      "id": "P-01",
      "dataset": "raw/prices.csv",
      "field": "date",
      "source": "chart.result[0].timestamp",
      "formula": "Unix seconds converted with meta.exchangeTimezoneName, then .date()",
      "units": "exchange-local trading date",
      "null_rule": "Never null; full 10-ticker cross-section required per date",
      "reviewed_as": "accepted",
      "correction": "",
      "catalog_reference": "raw/prices.csv,date"
    },
    {
      "id": "P-02",
      "dataset": "raw/prices.csv",
      "field": "ticker",
      "source": "chart.result[0].meta.symbol",
      "formula": "Read from the response meta block",
      "units": "symbol",
      "null_rule": "Never null; must equal the 10 configured tickers",
      "reviewed_as": "corrected",
      "correction": "The ticker is set by the request loop from config.ASSETS and stamped onto the parsed frame; meta.symbol is never parsed. A renamed or re-listed ticker would silently rename a series mid-sample.",
      "catalog_reference": "raw/prices.csv,ticker"
    },
    {
      "id": "P-03",
      "dataset": "raw/prices.csv",
      "field": "adjusted_close",
      "source": "chart.result[0].indicators.quote[0].close",
      "formula": "Close price divided by previous close",
      "units": "USD per share",
      "null_rule": "Values accepted as delivered; missing dates forward-filled",
      "reviewed_as": "corrected",
      "correction": "Values come from indicators.adjclose[0].adjclose, requested explicitly with includeAdjustedClose=true, and are taken as delivered. The transform is a plain split/distribution-adjusted price, not a ratio, and nothing is forward-filled: a null, non-finite or non-positive price raises.",
      "catalog_reference": "raw/prices.csv,adjusted_close"
    },
    {
      "id": "P-04",
      "dataset": "raw/macro.csv",
      "field": "date",
      "source": "observation_date",
      "formula": "pd.to_datetime",
      "units": "observation date",
      "null_rule": "Never null",
      "reviewed_as": "corrected",
      "correction": "Null rule is wrong. FRED emits blank-valued rows for market closures; those rows are dropped during ingest, so the loaded series has gaps by design and the study-month completeness check lives in factor_research instead.",
      "catalog_reference": "raw/macro.csv,date"
    },
    {
      "id": "P-05",
      "dataset": "raw/macro.csv",
      "field": "series",
      "source": "series_id column in fredgraph.csv",
      "formula": "Read from the response header",
      "units": "FRED series id",
      "null_rule": "Never null; must equal configured series set",
      "reviewed_as": "corrected",
      "correction": "fredgraph.csv has no series column, only observation_date and the value. The label is assigned from config.MACRO in the download loop.",
      "catalog_reference": "raw/macro.csv,series"
    },
    {
      "id": "P-06",
      "dataset": "monthly_macro.csv",
      "field": "DGS10",
      "source": "raw/macro.csv series=DGS10",
      "formula": "Last observed value in month",
      "units": "decimal monthly change",
      "null_rule": "Nulls forward-filled between observations",
      "reviewed_as": "corrected",
      "correction": "Units are percent per annum, never converted to decimals. rate_sensitivity is therefore a slope per 1 percentage point of yield change. Missing months raise instead of being filled.",
      "catalog_reference": "monthly_macro.csv,DGS10"
    },
    {
      "id": "P-07",
      "dataset": "assets.csv",
      "field": "name",
      "source": "issuer fund pages",
      "formula": "Fund legal name from the issuer website",
      "units": "text",
      "null_rule": "Never null",
      "reviewed_as": "corrected",
      "correction": "Names come from config.ASSETS and are research labels, not an issuer security master. The issuer pages are cited as comparator rationale and are not parsed.",
      "catalog_reference": "assets.csv,name"
    },
    {
      "id": "P-08",
      "dataset": "monthly_returns.csv",
      "field": "MINT",
      "source": "monthly_prices.csv column MINT",
      "formula": "P_t / P_(t-1) - 1",
      "units": "decimal monthly return (0.01 = 1%)",
      "null_rule": "Never null; pipeline raises on any missing return",
      "reviewed_as": "accepted",
      "correction": "",
      "catalog_reference": "monthly_returns.csv,MINT"
    },
    {
      "id": "P-09",
      "dataset": "fund_metrics.csv",
      "field": "tracking_error",
      "source": "analytics.metrics(); comparator = benchmark_proxy monthly return",
      "formula": "std(r - comparator, ddof=1) x sqrt(12)",
      "units": "decimal per year",
      "null_rule": "Never null (0 when identical)",
      "reviewed_as": "accepted",
      "correction": "",
      "catalog_reference": "fund_metrics.csv,tracking_error"
    },
    {
      "id": "P-10",
      "dataset": "raw/prices.csv",
      "field": "close_price",
      "source": "chart.result[0].indicators.quote[0].close",
      "formula": "Unadjusted exchange close",
      "units": "USD per share",
      "null_rule": "Never null",
      "reviewed_as": "unknown_field",
      "correction": "Rejected. No unadjusted close is stored; the normalized cache holds adjclose only, so a downstream edit cannot silently swap the price basis.",
      "catalog_reference": "docs/field_catalog.csv has no raw/prices.csv,close_price row"
    }
  ]
}
```

## Review

`scripts/check_field_mapping.py` reads the block above and re-derives each verdict from the catalog. Source, formula and null rule are matched as fragments, so a proposal that cites a genuine sub-path passes; **units are compared verbatim**, because "USD per share" is a substring of "USD per share, split/distribution adjusted" and would otherwise pass while quietly dropping the adjustment.

| ID | Field | Verdict | Attributes the catalog contradicted |
|---|---|---|---|
| P-01 | `raw/prices.csv,date` | accepted | — |
| P-02 | `raw/prices.csv,ticker` | corrected | source, formula |
| P-03 | `raw/prices.csv,adjusted_close` | corrected | source, formula, units, null rule |
| P-04 | `raw/macro.csv,date` | corrected | null rule |
| P-05 | `raw/macro.csv,series` | corrected | source, formula |
| P-06 | `monthly_macro.csv,DGS10` | corrected | units, null rule |
| P-07 | `assets.csv,name` | corrected | source, formula |
| P-08 | `monthly_returns.csv,MINT` | accepted | — |
| P-09 | `fund_metrics.csv,tracking_error` | accepted | — |
| P-10 | `raw/prices.csv,close_price` | unknown to the catalog | field does not exist |

```text
P-01  raw/prices.csv,date              accepted       -
P-02  raw/prices.csv,ticker            corrected      source, formula
P-03  raw/prices.csv,adjusted_close    corrected      source, formula, units, null_rule
P-04  raw/macro.csv,date               corrected      null_rule
P-05  raw/macro.csv,series             corrected      source, formula
P-06  monthly_macro.csv,DGS10          corrected      units, null_rule
P-07  assets.csv,name                  corrected      source, formula
P-08  monthly_returns.csv,MINT         accepted       -
P-09  fund_metrics.csv,tracking_error  accepted       -
P-10  raw/prices.csv,close_price       unknown_field  field is not in the catalog

10 proposals: 3 accepted, 6 corrected, 1 unknown to the catalog.
Review matches the catalog.
```

## What the draft got wrong, and why it matters

- **P-03 is the dangerous one.** `quote[0].close` is the unadjusted close. Mapping the stored column to it would have left the code and the catalog agreeing on a *number that is not what the pipeline computes* — distributions and splits would vanish from fund and ETF returns, and the cache would still hash correctly. `parse_yahoo` reads `adjclose[0].adjclose` and requests it explicitly, and [data_sources.md](file:///C:/Users/hp/Documents/Qoder/2026-10-30/3b436995/repo/docs/data_sources.md) records that unadjusted close is never substituted.
- **P-06 changes the meaning of a headline metric.** Percent-per annum read as a decimal monthly change is a scale error of roughly 1200x, and it would have made `return_per_1pp_yield_change` nonsense. The catalog and `analytics.factor_research()` both keep yields in percent.
- **P-04 and P-06 both invented null handling.** The draft assumed forward filling; the pipeline drops blank FRED rows and raises if a study month is missing. Filling silently would have manufactured zero changes out of market closures.
- **P-02 and P-05 attributed fields to the payload that the payload does not carry.** `fredgraph.csv` has no series column at all, and the ticker column is stamped from the request. Both would have made the catalog describe a parse that does not exist.
- **P-07 mistook a research label for a security master.** Names come from `config.ASSETS`; the issuer pages are comparator rationale and are never parsed.
- **P-10 proposed a field the repository deliberately does not store.** Keeping only `adjclose` is what stops a later edit from switching price basis.

Three proposals survived unchanged, so the review is not a blanket rejection: the month-end return formula, the tracking-error formula with `ddof=1` and `sqrt(12)`, and the timestamp-to-exchange-timezone date rule were drafted correctly and match the catalog's cited tests.

## Reproduce the check

```bash
export PYTHONPATH=src
python scripts/check_field_mapping.py
python scripts/check_field_mapping.py --json   # machine-readable verdicts
python -m pytest tests/test_field_mapping.py -q
```

The checker exits 1 if a recorded verdict disagrees with the catalog, if a corrected proposal carries no correction text or catalog reference, or if the review block loses its approval field. Editing the catalog or this document without re-running it is the failure mode the test is there to catch.

## Approval

The catalog rows and the code agree, and the check passes, but approval is a human act. **This mapping is not signed off.** `Lifewitdata` as research maintainer should either record approval here — date, scope, and anything held back — or amend the draft. Until then treat `docs/field_catalog.csv` as authoritative and this file as a worked example of reviewing an AI draft, not as an approved artifact.

## Limits of this example

One prompt, one payload family, ten fields. It demonstrates the review loop, not coverage of all 118 catalog rows, and the assistant that drafted the mapping also ran the review — an independent human pass is exactly what is still missing.
