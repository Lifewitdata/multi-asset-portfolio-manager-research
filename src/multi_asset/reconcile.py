"""Keyed, column-level comparison of loaded SQL tables against the frames they were loaded from."""
import json
from datetime import datetime, timezone
from pathlib import Path
import numpy as np
import pandas as pd
from .config import ROOT

# Both sides hold IEEE-754 doubles (pandas float64 / SQL Server FLOAT(53)), so a correct load
# differs by zero. A 1e-9 relative tolerance hid a deliberate one-part-per-billion price edit.
ABS_TOL = 1e-12
REL_TOL = 1e-12
DATE_COLUMNS = {"date", "training_end"}
MISMATCH_COLUMNS = ["table", "key", "column", "issue", "source_value", "target_value", "abs_diff", "tolerance"]


def _normalise(frame, column):
    values = frame[column]
    if column in DATE_COLUMNS:
        return pd.to_datetime(values, errors="raise").dt.strftime("%Y-%m-%d").where(values.notna())
    return values


def _key_text(row, keys):
    return json.dumps({k: str(row[k]) for k in keys}, sort_keys=True)


def compare(table, source, target, keys, abs_tol=ABS_TOL, rel_tol=REL_TOL):
    """Return (summary dict, mismatch DataFrame) for one table."""
    issues = []
    source_cols, target_cols = list(source.columns), list(target.columns)
    for column in source_cols:
        if column not in target_cols:
            issues.append({"table": table, "key": "", "column": column, "issue": "missing_column"})
    for column in target_cols:
        if column not in source_cols:
            issues.append({"table": table, "key": "", "column": column, "issue": "unexpected_column"})
    shared = [c for c in source_cols if c in target_cols]
    s = pd.DataFrame({c: _normalise(source, c) for c in shared})
    t = pd.DataFrame({c: _normalise(target, c) for c in shared})
    for k in keys:
        s[k], t[k] = s[k].astype(str), t[k].astype(str)
    for name, frame in [("source", s), ("target", t)]:
        if frame.duplicated(keys).any():
            raise ValueError(f"{table}: duplicate keys in {name}; comparison would be ambiguous")
    joined = s.merge(t, on=keys, how="outer", suffixes=("_src", "_tgt"), indicator=True)
    for _, row in joined[joined._merge != "both"].iterrows():
        issue = "missing_in_target" if row._merge == "left_only" else "unexpected_in_target"
        issues.append({"table": table, "key": _key_text(row, keys), "column": "<row>", "issue": issue})
    both = joined[joined._merge == "both"]
    values = [c for c in shared if c not in keys]
    max_diff = 0.0
    for column in values:
        a, b = both[f"{column}_src"], both[f"{column}_tgt"]
        a_null, b_null = a.isna(), b.isna()
        null_flip = a_null != b_null
        numeric = column not in DATE_COLUMNS and pd.api.types.is_numeric_dtype(source[column])
        if numeric:
            x, y = pd.to_numeric(a, errors="coerce"), pd.to_numeric(b, errors="coerce")
            diff = (x - y).abs()
            tol = abs_tol + rel_tol * x.abs()
            bad = (~a_null & ~b_null) & ~(diff <= tol)
            if diff.notna().any():
                max_diff = max(max_diff, float(diff.max()))
        else:
            diff, tol = pd.Series(np.nan, index=a.index), pd.Series(np.nan, index=a.index)
            bad = (~a_null & ~b_null) & (a.astype(str) != b.astype(str))
        for idx in both.index[null_flip | bad]:
            issues.append({"table": table, "key": _key_text(both.loc[idx], keys), "column": column,
                           "issue": "null_mismatch" if null_flip[idx] else "value_diff",
                           "source_value": a[idx], "target_value": b[idx],
                           "abs_diff": diff[idx], "tolerance": tol[idx]})
    mismatches = pd.DataFrame(issues, columns=MISMATCH_COLUMNS)
    summary = {"table": table, "keys": keys, "source_rows": len(source), "target_rows": len(target),
               "matched_rows": int(len(both)), "value_columns": len(values),
               "cells_compared": int(len(both) * len(values)), "max_abs_diff": max_diff,
               "mismatches": int(len(mismatches)), "status": "PASS" if mismatches.empty else "FAIL"}
    return summary, mismatches


def reconcile(frames, read_table, keys):
    """Compare every frame with read_table(name); keys maps table name to primary-key columns."""
    summaries, mismatches = [], []
    for name, frame in frames.items():
        summary, issues = compare(name, frame, read_table(name), keys[name])
        summaries.append(summary)
        mismatches.append(issues)
    found = [m for m in mismatches if not m.empty]
    return summaries, pd.concat(found, ignore_index=True) if found else pd.DataFrame(columns=MISMATCH_COLUMNS)


def export(summaries, mismatches, folder=None, label="sqlserver"):
    folder = Path(folder or ROOT/"reports/local/reconciliation")
    folder.mkdir(parents=True, exist_ok=True)
    mismatches.to_csv(folder/"mismatches.csv", index=False, lineterminator="\n")
    report = {"generated_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"), "target": label,
              "abs_tolerance": ABS_TOL, "rel_tolerance": REL_TOL,
              "tables": summaries, "total_cells_compared": sum(s["cells_compared"] for s in summaries),
              "total_mismatches": int(len(mismatches)),
              "status": "PASS" if mismatches.empty else "FAIL"}
    with (folder/"summary.json").open("w", encoding="utf-8", newline="\n") as handle:
        json.dump(report, handle, indent=2, default=str)
    return report


def main():
    import argparse
    from sqlalchemy import text
    from .database import KEYS, engine, prepared_frames
    parser = argparse.ArgumentParser(description="Compare every loaded SQL table with the frame it was loaded from.")
    parser.add_argument("--output", help="Folder for summary.json and mismatches.csv. Default reports/local/reconciliation/")
    args = parser.parse_args()
    frames = prepared_frames()
    db = engine()
    label = f"{db.url.database}@{db.url.host}"
    try:
        with db.connect() as conn:
            summaries, mismatches = reconcile(frames, lambda n: pd.read_sql(text(f"SELECT * FROM research.[{n}]"), conn), KEYS)
    finally:
        db.dispose()
    folder = Path(args.output) if args.output else ROOT / "reports/local/reconciliation"
    report = export(summaries, mismatches, folder=folder, label=label)
    for s in summaries:
        print(f"{s['table']}: {s['matched_rows']}/{s['source_rows']} rows, {s['cells_compared']} cells, "
              f"max diff {s['max_abs_diff']:.3g}, mismatches {s['mismatches']} -> {s['status']}")
    print(f"{report['status']}: {report['total_cells_compared']} cells compared against {label}, "
          f"{report['total_mismatches']} mismatches. Exports in {folder}/")
    if report["status"] != "PASS":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
