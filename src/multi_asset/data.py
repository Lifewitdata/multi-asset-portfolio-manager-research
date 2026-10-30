"""Explicit download/cache workflow. Failed feeds never become simulated observations."""
import argparse
import hashlib
import io
import json
import time
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo
import numpy as np
import pandas as pd
from .config import ROOT, ASSETS, MACRO, START, END, STALE_RUN_DAYS, STALE_RUN_OVERRIDES

def download(url):
    error = None
    for attempt in range(3):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (portfolio-research)"})
            with urllib.request.urlopen(req, timeout=45) as response:
                return response.read()
        except Exception as exc:
            error = exc
            if attempt < 2:
                time.sleep(1 + attempt)
    raise RuntimeError(f"Download failed: {url}. No synthetic fallback. Retry later.") from error

def parse_yahoo(payload, ticker):
    obj = json.loads(payload)
    if obj.get("chart", {}).get("error"):
        raise ValueError(f"Yahoo error for {ticker}: {obj['chart']['error']}")
    result = obj["chart"]["result"][0]
    if result["meta"]["currency"] != "USD":
        raise ValueError(f"Unexpected currency for {ticker}")
    timestamps = result["timestamp"]
    dates = [datetime.fromtimestamp(t, ZoneInfo(result["meta"]["exchangeTimezoneName"])).date() for t in timestamps]
    values = result["indicators"]["adjclose"][0]["adjclose"]
    return pd.DataFrame({"date": pd.to_datetime(dates), "ticker": ticker, "adjusted_close": values})

def validate_prices(prices):
    p = prices.copy()
    p["date"] = pd.to_datetime(p["date"], errors="raise")
    if p.empty or p.duplicated(["date", "ticker"]).any():
        raise ValueError("Empty prices or duplicate date/ticker keys")
    if set(p.ticker) != set(ASSETS):
        raise ValueError("Missing or unexpected ticker")
    if not (p.groupby("date").ticker.nunique() == len(ASSETS)).all():
        raise ValueError("Incomplete daily cross-section; no silent missing-day returns")
    values = pd.to_numeric(p.adjusted_close, errors="raise")
    if not np.isfinite(values).all() or (values <= 0).any():
        raise ValueError("Prices must be finite and positive; no forward filling")
    p["adjusted_close"] = values
    if (p.date > pd.Timestamp(END)).any() or (p.date < pd.Timestamp(START)).any():
        raise ValueError("Prices outside fixed study period")
    p = p.sort_values(["date", "ticker"]).reset_index(drop=True)
    check_unchanged_runs(p)
    return p

def unchanged_runs(prices):
    """Runs of consecutive trading days whose close equals the previous day's close."""
    rows = []
    for ticker, group in prices.sort_values("date").groupby("ticker"):
        same = group.adjusted_close.diff().eq(0).to_numpy()
        dates, values = group.date.to_numpy(), group.adjusted_close.to_numpy()
        start = None
        for i, flag in enumerate(np.append(same, False)):
            if flag and start is None:
                start = i
            elif not flag and start is not None:
                rows.append({"ticker": ticker, "first_repeat": pd.Timestamp(dates[start]), "last_repeat": pd.Timestamp(dates[i-1]),
                             "repeated_days": i-start, "value": float(values[start])})
                start = None
    return pd.DataFrame(rows, columns=["ticker", "first_repeat", "last_repeat", "repeated_days", "value"])

def check_unchanged_runs(prices):
    """A provider can keep publishing rows while repeating a frozen price; row and gap checks cannot see that."""
    runs = unchanged_runs(prices)
    limit = runs.ticker.map(lambda t: STALE_RUN_OVERRIDES.get(t, STALE_RUN_DAYS))
    bad = runs[runs.repeated_days > limit]
    if not bad.empty:
        r = bad.iloc[0]
        raise ValueError(f"Possible stale feed: {r.ticker} close {r.value} repeated for {r.repeated_days} trading days "
                         f"({r.first_repeat:%Y-%m-%d} to {r.last_repeat:%Y-%m-%d}); {len(bad)} run(s) over limit. See docs/incidents/")

def monthly_prices(prices):
    prices = validate_prices(prices)
    rows = []
    expected = pd.period_range(START, END, freq="M").to_timestamp("M")
    for ticker, group in prices.groupby("ticker"):
        series = group.set_index("date").adjusted_close.sort_index()
        monthly = series.resample("ME").last().reindex(expected)
        last_dates = pd.Series(series.index, index=series.index).resample("ME").last().reindex(expected)
        stale = (pd.Series(expected, index=expected) - last_dates).dt.days
        if monthly.isna().any() or (stale > 7).any():
            raise ValueError(f"Missing or stale month-end observations for {ticker}")
        rows.append(monthly.rename(ticker))
    return pd.concat(rows, axis=1).rename_axis("date")

def fetch(root=ROOT):
    raw = Path(root)/"data/raw"
    raw.mkdir(parents=True, exist_ok=True)
    begin = int(pd.Timestamp(START, tz="UTC").timestamp())
    finish = int((pd.Timestamp(END, tz="UTC") + pd.Timedelta(days=1)).timestamp())
    manifest, frames, payloads = [], [], {}
    for ticker in ASSETS:
        url = f"https://query1.finance.yahoo.com/v8/finance/chart/{ticker}?period1={begin}&period2={finish}&interval=1d&events=div%2Csplits&includeAdjustedClose=true"
        payload = download(url)
        frame = parse_yahoo(payload, ticker)
        frame = frame[frame.date.between(START, END)]
        frames.append(frame)
        name = f"yahoo_{ticker}.json"
        payloads[name] = payload
        manifest.append({"file": name, "source": "Yahoo Finance", "series": ticker, "url": url,
                         "sha256": hashlib.sha256(payload).hexdigest(), "rows": len(frame),
                         "retrieved_utc": datetime.now(timezone.utc).isoformat()})
        print(f"Downloaded {ticker}: {len(frame)} daily observations", flush=True)
    prices = validate_prices(pd.concat(frames, ignore_index=True))
    monthly_prices(prices)  # reject incomplete downloads before replacing cache
    macro_frames = []
    for code in MACRO:
        url = f"https://fred.stlouisfed.org/graph/fredgraph.csv?id={code}&cosd={START}&coed={END}"
        payload = download(url)
        m = pd.read_csv(io.BytesIO(payload))
        m.columns = ["date", "value"]
        m["date"] = pd.to_datetime(m.date)
        m["value"] = pd.to_numeric(m.value, errors="coerce")
        m = m[m.date.between(START, END)].dropna(subset=["value"])
        if m.empty or m.date.duplicated().any():
            raise ValueError(f"Empty/duplicate FRED series {code}")
        m["series"] = code
        macro_frames.append(m)
        name = f"fred_{code}.csv"
        payloads[name] = payload
        manifest.append({"file": name, "source": "Federal Reserve Board via FRED", "series": code,
                         "url": url, "sha256": hashlib.sha256(payload).hexdigest(), "rows": len(m),
                         "retrieved_utc": datetime.now(timezone.utc).isoformat()})
    # Commit manifest last; interrupted writes fail checksum verification on the next run.
    for name, payload in payloads.items():
        (raw/name).write_bytes(payload)
    prices.to_csv(raw/"prices.csv", index=False)
    pd.concat(macro_frames).to_csv(raw/"macro.csv", index=False)
    for name in ["prices.csv", "macro.csv"]:
        manifest.append({"file": name, "source": "normalized downloaded data",
                         "sha256": hashlib.sha256((raw/name).read_bytes()).hexdigest()})
    (raw/"manifest.json").write_text(json.dumps(manifest, indent=2))
    return load(root)

def load(root=ROOT):
    raw = Path(root)/"data/raw"
    if not (raw/"manifest.json").exists():
        raise FileNotFoundError("No historical cache. Run: python -m multi_asset.pipeline --download")
    manifest = json.loads((raw/"manifest.json").read_text())
    for record in manifest:
        path = raw/record["file"]
        if hashlib.sha256(path.read_bytes()).hexdigest() != record["sha256"]:
            raise ValueError(f"Cache checksum mismatch: {path.name}; rerun --download")
    p = validate_prices(pd.read_csv(raw/"prices.csv", parse_dates=["date"]))
    m = pd.read_csv(raw/"macro.csv", parse_dates=["date"])
    if m.duplicated(["date", "series"]).any() or set(m.series) != set(MACRO) or not np.isfinite(m.value).all():
        raise ValueError("Invalid macro data")
    return p, m, manifest

def verify_processed(root=ROOT):
    """Reject edited, mixed or stale report files before SQL loading or display."""
    root = Path(root)
    _, _, manifest = load(root)
    quality = json.loads((root/"reports/local/data_quality.json").read_text())
    if quality["source_manifest"] != manifest:
        raise ValueError("Processed outputs use another source snapshot; rerun the pipeline")
    for name, checksum in quality["processed_sha256"].items():
        if hashlib.sha256((root/"data/processed"/name).read_bytes()).hexdigest() != checksum:
            raise ValueError(f"Processed checksum mismatch: {name}; rerun the pipeline")

if __name__ == "__main__":
    fetch()
