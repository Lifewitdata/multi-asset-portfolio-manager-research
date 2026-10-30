"""SQL Server persistence with validated staging, transactional MERGE and count checks."""
import os
import re
import uuid
import pandas as pd
from sqlalchemy import create_engine, text
from .config import ROOT
from .data import load, verify_processed

# Names are constants, never derived from user input.
KEYS={"assets":["ticker"],"daily_prices":["date","ticker"],"daily_macro":["date","series"],
      "monthly_returns":["date"],"portfolio_returns":["date","portfolio"],"weights":["date","portfolio","ticker"],
      "portfolio_metrics":["portfolio"],"fund_metrics":["fund"],"rolling_fund_metrics":["date","fund"],
      "factor_coefficients":["fund","term"],"rate_sensitivity":["fund"],"volatility_scores":["model"]}

def engine():
    url=os.getenv("MULTI_ASSET_SQLSERVER_URL")
    if not url:raise RuntimeError("Set MULTI_ASSET_SQLSERVER_URL. See docs/windows_setup.md")
    return create_engine(url,fast_executemany=True,pool_pre_ping=True)

def merge_sql(table,stage,columns,keys):
    if table not in KEYS or not re.fullmatch(r"stage_[a-f0-9]{12}",stage):raise ValueError("Invalid table name")
    if any(not re.fullmatch(r"[A-Za-z][A-Za-z0-9_]*",c) for c in columns):raise ValueError("Invalid column")
    on=" AND ".join(f"t.[{c}]=s.[{c}]" for c in keys)
    update=", ".join(f"t.[{c}]=s.[{c}]" for c in columns if c not in keys)
    cols=", ".join(f"[{c}]" for c in columns)
    vals=", ".join(f"s.[{c}]" for c in columns)
    return f"MERGE research.[{table}] WITH (HOLDLOCK) AS t USING research.[{stage}] AS s ON {on} WHEN MATCHED THEN UPDATE SET {update} WHEN NOT MATCHED THEN INSERT ({cols}) VALUES ({vals});"

def prepared_frames():
    verify_processed()
    prices,macro,_=load()
    frames={"daily_prices":prices,"daily_macro":macro}
    for name in KEYS:
        if name not in frames:frames[name]=pd.read_csv(ROOT/f"data/processed/{name}.csv")
    for name,frame in frames.items():
        if frame.empty or frame.duplicated(KEYS[name]).any():raise ValueError(f"Empty or duplicate {name}")
        for col in ["date","training_end"]:
            if col in frame:frame[col]=pd.to_datetime(frame[col]).dt.date
    return {name:frames[name] for name in KEYS}  # dimensions precede facts for foreign keys

def load_sqlserver():
    frames=prepared_frames()
    db=engine()
    try:
        with db.begin() as conn:
            script=(ROOT/"sql/01_schema.sql").read_text()
            for batch in re.split(r"^GO\s*$",script,flags=re.MULTILINE|re.IGNORECASE):
                if batch.strip():conn.exec_driver_sql(batch)
            for name,frame in frames.items():
                stage="stage_"+uuid.uuid4().hex[:12]
                frame.to_sql(stage,conn,schema="research",if_exists="fail",index=False,chunksize=500)
                conn.exec_driver_sql(merge_sql(name,stage,list(frame.columns),KEYS[name]))
                actual=conn.execute(text(f"SELECT COUNT_BIG(*) FROM research.[{name}]" )).scalar_one()
                if actual!=len(frame):raise ValueError(f"Count mismatch {name}: expected {len(frame)}, got {actual}; transaction rolled back")
                conn.exec_driver_sql(f"DROP TABLE research.[{stage}]")
                print(f"{name}: {actual}")
        print("SQL Server load committed; all table counts reconciled.")
    finally:db.dispose()

def read_dashboard(names):
    if any(n not in KEYS for n in names):raise ValueError("Unexpected dashboard table")
    db=engine()
    try:
        with db.connect() as conn:
            return {n:pd.read_sql(text(f"SELECT * FROM research.[{n}]"),conn) for n in names}
    finally:db.dispose()

if __name__=="__main__":load_sqlserver()
