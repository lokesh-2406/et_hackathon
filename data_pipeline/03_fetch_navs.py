"""03_fetch_navs.py - Bulk Ingest AMFI Scheme Master and Historical NAVs via TigZig API."""

import argparse
import logging
import requests
import pandas as pd
from pathlib import Path

from data_pipeline.config import PROCESSED_DIR, ROOT

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')

TIGZIG_BASE = "https://api.tigzig.com/mf/v1/download"

def download_file(url, out_path):
    logging.info(f"Downloading from {url} to {out_path}...")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with requests.get(url, stream=True) as r:
        r.raise_for_status()
        with open(out_path, 'wb') as f:
            for chunk in r.iter_content(chunk_size=8192):
                f.write(chunk)
    logging.info(f"Downloaded {out_path.stat().st_size / (1024*1024):.2f} MB")

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("action", choices=["master", "history", "bulk"], help="Action to perform (all use bulk now)")
    ap.add_argument("--force", action="store_true", help="Bypass cached files")
    args = ap.parse_args()

    raw_dir = ROOT / "data" / "raw"
    raw_dir.mkdir(parents=True, exist_ok=True)
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)

    latest_parquet_path = raw_dir / "amfi_nav_master_latest.parquet"
    full_parquet_path = raw_dir / "amfi_nav_master.parquet"

    if args.action in ["master", "bulk"]:
        if args.force or not latest_parquet_path.exists():
            download_file(f"{TIGZIG_BASE}?format=latest.parquet", latest_parquet_path)
            
        logging.info("Normalizing master data...")
        df = pd.read_parquet(latest_parquet_path)
        
        # Rename columns to match our expected canonical schema
        rename_map = {
            "aaum_cr_quarterly_avg": "aaum_cr",
            "scheme_plan": "plan",
            "scheme_option": "option",
            "first_date": "inception_date",
            "last_date": "nav_date"
        }
        df = df.rename(columns=rename_map)
        if "category_sub" in df.columns:
            df["category"] = df["category_sub"]
        
        # Filter out only active ones for main master, or keep all? The prompt said to keep historical.
        # But for agents we mostly care about active ones or recently matured. Let's keep all.
        df.to_csv(PROCESSED_DIR / "nav_master.csv", index=False)
        logging.info(f"Saved {len(df)} schemes to nav_master.csv")

    if args.action in ["history", "bulk"]:
        if args.force or not full_parquet_path.exists():
            download_file(f"{TIGZIG_BASE}?format=parquet", full_parquet_path)
            
        logging.info("Normalizing history data...")
        # We can just copy it or read and re-save if we need to filter.
        # TigZig parquet is already columnar and matches: scheme_code, date, nav, scheme_name, isin.
        # It's huge, so we just copy it to processed if we don't need to change it, or read/write it.
        # For our pipeline, `nav_history.parquet` is expected to have: scheme_code, date, nav.
        
        # Read the parquet using pandas/pyarrow
        df_hist = pd.read_parquet(full_parquet_path, columns=["scheme_code", "date", "nav"])
        
        out_file = PROCESSED_DIR / "nav_history.parquet"
        df_hist.to_parquet(out_file, index=False)
        logging.info(f"Saved {len(df_hist)} historical NAV records to {out_file}")

if __name__ == "__main__":
    main()
