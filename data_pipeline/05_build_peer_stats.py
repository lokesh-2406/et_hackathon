"""05_build_peer_stats.py - Compute trailing returns, risk stats, and percentiles."""

import argparse
import logging
import numpy as np
import pandas as pd
from pathlib import Path

from data_pipeline.config import PROCESSED_DIR, RISK_FREE_RATE

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')

def cagr(s, years):
    end = s.index[-1]
    start_dt = end - pd.DateOffset(years=years)
    past = s[s.index <= start_dt]
    if past.empty:
        return np.nan
    return (s.iloc[-1] / past.iloc[-1]) ** (1 / years) - 1

def compute_stats(s):
    s = s[~s.index.duplicated()].sort_index()
    if len(s) < 200: # Slightly lower threshold for shorter data sets
        return None
        
    r = s.pct_change().dropna()
    last3 = r[r.index > s.index[-1] - pd.DateOffset(years=3)]
    s3 = s[s.index > s.index[-1] - pd.DateOffset(years=3)]
    
    dd = (s3 / s3.cummax() - 1).min() if len(s3) > 50 else np.nan
    vol = last3.std() * np.sqrt(252) if len(last3) > 200 else np.nan
    
    c1 = cagr(s, 1)
    c3 = cagr(s, 3)
    c5 = cagr(s, 5)
    
    sharpe = (c3 - RISK_FREE_RATE) / vol if vol and not np.isnan(c3) else np.nan
    
    return {
        "ret_1y": c1,
        "cagr_3y": c3,
        "cagr_5y": c5,
        "vol_3y": vol,
        "maxdd_3y": dd,
        "sharpe_3y": sharpe
    }

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, help="Limit number of schemes for testing")
    args = ap.parse_args()
    
    hist_file = PROCESSED_DIR / "nav_history.parquet"
    master_file = PROCESSED_DIR / "nav_master.csv"
    
    if not hist_file.exists() or not master_file.exists():
        logging.error("Required processed files not found. Run 03_fetch_navs.py first.")
        return
        
    logging.info("Loading NAV history and master...")
    hist = pd.read_parquet(hist_file)
    # Convert date strings to datetime to allow indexing
    hist['date'] = pd.to_datetime(hist['date'])
    
    master = pd.read_csv(master_file)
    master = master[master.option.str.upper() == "GROWTH"].set_index("scheme_code")
    
    rows = []
    processed = 0
    
    grouped = hist.groupby("scheme_code")
    if args.limit:
        keys = list(grouped.groups.keys())[:args.limit]
        grouped_iter = [(k, grouped.get_group(k)) for k in keys]
    else:
        grouped_iter = grouped
        
    logging.info(f"Computing stats for {len(grouped)} schemes...")
    
    for code, g in grouped_iter:
        if code not in master.index:
            continue
            
        series = g.set_index("date")["nav"]
        st = compute_stats(series)
        
        if st:
            m = master.loc[code]
            # Handle possible duplicate index from master
            if isinstance(m, pd.DataFrame):
                m = m.iloc[0]
                
            row_data = {
                "scheme_code": code,
                "scheme_name": m.scheme_name,
                "category": m.category,
                "plan": m.plan
            }
            row_data.update(st)
            rows.append(row_data)
            
        processed += 1
        if processed % 1000 == 0:
            logging.info(f"  Processed {processed} schemes...")
            
    if not rows:
        logging.warning("No peer stats could be computed (data might be too short).")
        return
        
    df = pd.DataFrame(rows)
    
    for col, p in (("ret_1y", "pct_1y"), ("cagr_3y", "pct_3y"), ("cagr_5y", "pct_5y")):
        df[p] = df.groupby(["category", "plan"])[col].rank(pct=True, na_option='bottom') * 100
        
    out_file = PROCESSED_DIR / "peer_stats.csv"
    df.to_csv(out_file, index=False)
    logging.info(f"Saved {len(df)} ranked schemes -> {out_file}")

if __name__ == "__main__":
    main()
