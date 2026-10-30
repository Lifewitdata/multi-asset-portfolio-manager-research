from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
# All tickers predate the fixed study period. USD market-price returns, unhedged.
ASSETS = {
    "SPY": ("US equities", "Equity"), "EFA": ("Developed ex-US equities", "Equity"),
    "EEM": ("Emerging-market equities", "Equity"), "IEF": ("US 7-10 year Treasuries", "Bond"),
    "LQD": ("US investment-grade credit", "Bond"), "GLD": ("Gold", "Gold"),
    "BIL": ("US Treasury bills", "Cash"), "AGG": ("US aggregate bonds", "Benchmark"),
    "BOND": ("PIMCO Active Bond", "Active fund"), "MINT": ("PIMCO Enhanced Short Maturity", "Active fund"),
}
INVESTABLE = ["SPY", "EFA", "EEM", "IEF", "LQD", "GLD", "BIL"]
PROFILES = {"Conservative": 0.25, "Balanced": 0.55, "Growth": 0.80}
MANAGERS = {"BOND": "AGG", "MINT": "BIL"}
MACRO = ["DGS10", "DGS2"]
START = "2013-12-01"
END = "2025-12-31"
LOOKBACK = 36
COST_BPS = 10.0  # per dollar traded; charge buys AND sells, not half-turnover
# Max consecutive trading days a close may repeat the previous close. Measured on the
# 2013-2025 cache: BIL 10 (near-zero T-bill yields, Aug 2016), MINT 3, all others <= 2.
STALE_RUN_DAYS = 5
STALE_RUN_OVERRIDES = {"BIL": 15}
