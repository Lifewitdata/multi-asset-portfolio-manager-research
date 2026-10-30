"""Reproduce INC-001 (simulated stale MINT price) on a temporary copy of the real cache.

The injected freeze is simulated. Everything else is the real 2013-2025 cache.
Usage: python scripts/stale_price_incident.py
"""
import hashlib
import json
import shutil
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/"src"))
from multi_asset import data, pipeline
from multi_asset.database import KEYS
from multi_asset.reconcile import compare

TICKER, FROZEN_FROM, FREEZE_START, FREEZE_END = "MINT", "2025-11-14", "2025-11-17", "2025-11-28"
OUT = ROOT/"reports/incidents"
TABLE_KEYS = {**KEYS, "monthly_prices":["date"], "monthly_macro":["date"], "volatility_predictions":["date","model"]}
# Portfolio tables use only the 7 investable ETFs, whose inputs stay bitwise identical, yet
# CVXPY/CLARABEL output moves by up to ~6e-10 (back to 2017) when other columns change.
MATERIAL = 1e-8

def inject(root):
    raw = root/"data/raw"
    prices = pd.read_csv(raw/"prices.csv")
    frozen = prices.loc[(prices.ticker==TICKER)&(prices.date==FROZEN_FROM), "adjusted_close"].item()
    mask = (prices.ticker==TICKER)&prices.date.between(FREEZE_START, FREEZE_END)
    before = prices[mask].copy()
    prices.loc[mask, "adjusted_close"] = frozen
    prices.to_csv(raw/"prices.csv", index=False, lineterminator="\n")
    # The provider "delivered" this file, so its checksum is recorded as genuine.
    manifest = json.loads((raw/"manifest.json").read_text(encoding="utf-8"))
    for record in manifest:
        if record["file"] == "prices.csv":
            record["sha256"] = hashlib.sha256((raw/"prices.csv").read_bytes()).hexdigest()
    (raw/"manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return frozen, before

def run_pipeline(root):
    with patch("multi_asset.data.check_unchanged_runs", lambda prices: None):
        with open(root/"pipeline.log", "w", encoding="utf-8") as log, patch("sys.stdout", log):
            pipeline.run(root=root)

def diff_tables(clean_root, dirty_root):
    scope, details = [], []
    for name, keys in TABLE_KEYS.items():
        path = {"daily_prices":"data/raw/prices.csv", "daily_macro":"data/raw/macro.csv"}.get(name, f"data/processed/{name}.csv")
        summary, mismatches = compare(name, pd.read_csv(clean_root/path), pd.read_csv(dirty_root/path), keys, abs_tol=1e-12, rel_tol=1e-12)
        material = mismatches[mismatches.abs_diff.isna() | (mismatches.abs_diff > MATERIAL)] if len(mismatches) else mismatches
        scope.append({"table": name, "rows": summary["source_rows"], "rows_changed": mismatches.key.nunique() if len(mismatches) else 0,
                      "rows_materially_changed": material.key.nunique() if len(material) else 0,
                      "columns_materially_changed": ";".join(sorted(material.column.unique())) if len(material) else "",
                      "max_abs_diff": summary["max_abs_diff"]})
        if len(mismatches):
            details.append(mismatches)
    return pd.DataFrame(scope), (pd.concat(details, ignore_index=True) if details else pd.DataFrame())

def main():
    OUT.mkdir(parents=True, exist_ok=True)
    data.verify_processed(ROOT)
    with tempfile.TemporaryDirectory() as control, tempfile.TemporaryDirectory() as tmp:
        control, tmp = Path(control), Path(tmp)
        shutil.copytree(ROOT/"data/raw", control/"data/raw")
        shutil.copytree(ROOT/"data/raw", tmp/"data/raw")
        frozen, before = inject(tmp)
        result = {"simulated": True, "ticker": TICKER, "frozen_close": frozen, "frozen_from": FROZEN_FROM,
                  "freeze_start": FREEZE_START, "freeze_end": FREEZE_END, "frozen_rows": len(before),
                  "true_closes": {r.date: r.adjusted_close for r in before.itertuples()}}

        # 1. Behaviour before the fix: the unchanged-run check did not exist.
        with patch("multi_asset.data.check_unchanged_runs", lambda prices: None):
            prices, _, _ = data.load(tmp)
            data.monthly_prices(prices)
        result["checks_before_fix"] = "PASS: checksums, duplicate keys, full cross-section, positive finite prices, month-end gap <= 7 days"

        # 2. The fix rejects the same delivery.
        try:
            data.load(tmp)
            result["check_after_fix"] = "NOT DETECTED"
        except ValueError as exc:
            result["check_after_fix"] = f"REJECTED: {exc}"
        runs = data.unchanged_runs(prices)
        result["longest_runs"] = {t: int(g.repeated_days.max()) for t, g in runs.groupby("ticker")}

        # 3. Scope: stale run vs a control run of the untouched cache under identical conditions.
        run_pipeline(control)
        run_pipeline(tmp)
        noise, _ = diff_tables(ROOT, control)
        result["control_vs_committed_baseline_max_abs_diff"] = {r.table: r.max_abs_diff for r in noise.itertuples() if r.rows_changed}
        scope, detail = diff_tables(control, tmp)
        scope.to_csv(OUT/"stale_price_scope.csv", index=False, lineterminator="\n")
        detail.to_csv(OUT/"stale_price_changed_cells.csv", index=False, lineterminator="\n")

        def pick(table, column, key):
            hit = detail[(detail.table==table)&(detail.column==column)&(detail.key.str.contains(key, regex=False))]
            return {"clean": float(hit.source_value.iloc[0]), "stale": float(hit.target_value.iloc[0])} if len(hit) else None
        result["impact"] = {
            "MINT 2025-11 monthly return": pick("monthly_returns", TICKER, "2025-11-30"),
            "MINT 2025-12 monthly return": pick("monthly_returns", TICKER, "2025-12-31"),
            "MINT tracking_error vs BIL": pick("fund_metrics", "tracking_error", TICKER),
            "MINT information_ratio": pick("fund_metrics", "information_ratio", TICKER),
            "MINT annual_mean_active_return": pick("fund_metrics", "annual_mean_active_return", TICKER),
            "MINT active_month_hit_rate": pick("fund_metrics", "active_month_hit_rate", TICKER)}
        result["tables_materially_changed"] = scope[scope.rows_materially_changed>0].table.tolist()
        result["tables_with_noise_only"] = scope[(scope.rows_changed>0)&(scope.rows_materially_changed==0)].table.tolist()
        result["tables_unchanged"] = scope[scope.rows_changed==0].table.tolist()
    (OUT/"stale_price_simulation.json").write_text(json.dumps(result, indent=2, default=str)+"\n", encoding="utf-8")
    print(scope.to_string(index=False))
    print(json.dumps({k: result[k] for k in ["checks_before_fix", "check_after_fix", "impact"]}, indent=2))

if __name__ == "__main__":
    main()
