"""Prove the CSV-vs-SQL reconciliation catches three storage faults.

A one-part-per-billion price edit, a deleted weight row and a one-in-ten-thousand metric edit
are applied inside an explicit transaction, compared, and then rolled back — the target database
holds exactly the same rows when this finishes as when it started.

Usage: python scripts/injected_fault_demo.py [--output reports/reconciliation]
"""
import argparse
import sys
from pathlib import Path
import pandas as pd
from sqlalchemy import text

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from multi_asset.database import KEYS, engine, prepared_frames
from multi_asset.reconcile import compare, export

FAULTS = [
    ("one part per billion added to one MINT close",
     "UPDATE research.[daily_prices] SET adjusted_close = adjusted_close * 1.000000001 "
     "WHERE ticker = N'MINT' AND [date] = '2025-11-28';"),
    ("one Growth Optimized GLD target weight deleted",
     "DELETE FROM research.[weights] WHERE [date] = '2025-12-31' "
     "AND portfolio = N'Growth Optimized' AND ticker = N'GLD';"),
    ("0.01 added to BOND tracking error",
     "UPDATE research.[fund_metrics] SET tracking_error = tracking_error + 0.0001 WHERE fund = N'BOND';"),
]


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--output", default=str(ROOT / "reports/reconciliation"))
    args = parser.parse_args()
    frames = prepared_frames()
    db = engine()
    label = f"{db.url.database}@{db.url.host} (injected faults, rolled back)"
    try:
        with db.connect() as conn:
            transaction = conn.begin()
            for description, statement in FAULTS:
                conn.exec_driver_sql(statement)
                print(f"injected: {description}")
            summaries, mismatches = [], []
            for name, frame in frames.items():
                stored = pd.read_sql(text(f"SELECT * FROM research.[{name}]"), conn)
                summary, issues = compare(name, frame, stored, KEYS[name])
                summaries.append(summary)
                mismatches.append(issues)
            found = [m for m in mismatches if not m.empty]
            detail = pd.concat(found, ignore_index=True) if found else pd.DataFrame()
            report = export(summaries, detail, folder=args.output, label=label)
            transaction.rollback()
    finally:
        db.dispose()
    out = Path(args.output)
    renames = {"summary.json": "injected_fault_summary.json", "mismatches.csv": "injected_fault_mismatches.csv"}
    for name, demo_name in renames.items():
        source = out / name
        if source.exists():  # keep the clean-run files when both reports share a folder
            source.replace(out / demo_name)
    for row in detail.to_dict("records"):
        print(f"caught: {row['table']} {row['column']} {row['issue']}")
    print(f"{report['status']}: {report['total_mismatches']} mismatches across "
          f"{report['total_cells_compared']} cells. Rolled back; database unchanged.")
    if report["total_mismatches"] != len(FAULTS):
        raise SystemExit(f"Expected {len(FAULTS)} caught faults, got {report['total_mismatches']}")


if __name__ == "__main__":
    main()
