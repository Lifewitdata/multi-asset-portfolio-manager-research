# Field catalog

[`field_catalog.csv`](field_catalog.csv) is the field-level companion to the [data dictionary](data_dictionary.md). It has one row per field: 118 fields across 16 datasets, covering raw inputs, processed CSVs and every column of the 12 SQL Server tables in `sql/01_schema.sql`.

| Column | Meaning |
|---|---|
| `dataset` | File under `data/` (raw) or `data/processed/` |
| `field` | Column name exactly as written to CSV and SQL |
| `sql_table` | `research.<table>` that stores it, blank if CSV-only |
| `type` | SQL type, or the pandas type for CSV-only fields |
| `units` | Decimal return, percent, USD per share, count, date, etc. |
| `source` | Provider field or upstream dataset it comes from |
| `formula` | How the value is computed, in words and code terms |
| `null_rule` | When nulls are rejected, when they are allowed and why |
| `key` | PK / FK role |
| `owner` | Accountable role. A single research maintainer owns all fields today; no separate data-owner or approver role exists |
| `verification_status` | One or more of the statuses below, separated by `;` |
| `evidence` | Files (or `file::function`) that prove the status. Blank only for `documented_only` |

## Verification status vocabulary

| Status | Meaning | Typical evidence |
|---|---|---|
| `validated_input` | A loader check rejects bad values (duplicates, gaps, non-positive prices, out-of-period dates) | `tests/test_data.py::…` |
| `unit_tested` | The formula is asserted by a unit test on deterministic fixtures | `tests/test_research.py::…` |
| `reconciled` | Value-compared CSV vs SQL Server cell by cell, 1e-12 tolerance | `reports/reconciliation/summary.json` |
| `traced` | Followed from raw observation to the dashboard in the calculation evidence report | `reports/calculation_evidence.md` |
| `documented_only` | Described here, but no automated check covers it | none |

The eight `documented_only` fields are stated openly rather than upgraded: six `raw/manifest.json` metadata fields (`file`, `source`, `series`, `url`, `rows`, `retrieved_utc`; the `sha256` field is checked on every load), `monthly_macro.csv` `date`, and `volatility_predictions.csv` `training_rows`.

## Keeping it honest

`tests/test_field_catalog.py` fails if:

- a SQL column exists without a catalog row, or a catalog row names a column the schema does not have;
- a CSV-only dataset's columns drift from what the pipeline writes;
- a required attribute is blank or a status is outside the vocabulary;
- an evidence path does not exist, or a `file::function` reference names a function that is not defined in that file.

It cannot check that a formula description is *correct*. That still depends on review.

## How this catalog was drafted, and who reviewed it

The raw-field mapping rows were drafted with AI assistance and then checked against the code. [ai_field_mapping.md](ai_field_mapping.md) records the prompt, the draft verbatim, the six corrections the catalog forced (including the unadjusted-close and percent-versus-decimal mistakes), and the machine check `scripts/check_field_mapping.py` that re-derives every verdict from this CSV. That document is **not signed off** by the maintainer yet; this catalog is the authoritative version.
