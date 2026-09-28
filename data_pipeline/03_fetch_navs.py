"""03_fetch_navs.py - Ingest AMFI Scheme Master and Historical NAVs."""

import argparse
import csv
import logging
from datetime import datetime
import pandas as pd
from io import StringIO

from data_pipeline.config import AMFI_NAV_ALL_URL, AMFI_NAV_FALLBACK_URL, MFAPI_BASE_URL, PROCESSED_DIR, ROOT
from data_pipeline.http_util import request_with_cache

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')


def fetch_amfi_nav_master(force=False):
    """Fetch the latest daily NAV text file from AMFI."""
    urls = [AMFI_NAV_ALL_URL, AMFI_NAV_FALLBACK_URL]
    
    for url in urls:
        logging.info(f"Trying to fetch NAV Master from {url}")
        content, meta = request_with_cache("GET", url, force=force, max_age_days=0.5, timeout=15)
        if content:
            return content
            
    return None

def parse_amfi_nav_master(content_str):
    """
    Parse AMFI semicolon-delimited file.
    Expected Format: SchemeCode;ISIN1;ISIN2;SchemeName;NAV;Date
    With category headers scattered throughout.
    """
    lines = content_str.split('\n')
    current_category = "Unknown"
    current_amc = "Unknown"
    
    records = []
    
    for line in lines:
        line = line.strip()
        if not line:
            continue
            
        if ';' not in line:
            # It's a header line (either AMC or Category)
            if "Mutual Fund" in line:
                current_amc = line
            elif "Schemes" in line or "Fund" in line:
                current_category = line
            continue
            
        parts = line.split(';')
        if len(parts) >= 6 and parts[0] != "Scheme Code":
            try:
                code, isin1, isin2, name, nav, d_str = parts[:6]
                if not code.strip():
                    continue
                    
                nav_val = float(nav.strip()) if nav.strip() not in ("N.A.", "") else None
                
                # Try to determine plan/option from name
                name_upper = name.upper()
                plan = "Direct" if "DIRECT" in name_upper else "Regular"
                option = "Growth" if "GROWTH" in name_upper else ("IDCW" if "IDCW" in name_upper or "DIVIDEND" in name_upper else "Other")
                
                records.append({
                    "scheme_code": int(code.strip()),
                    "isin_growth": isin1.strip(),
                    "isin_reinv": isin2.strip(),
                    "scheme_name": name.strip(),
                    "category": current_category,
                    "amc": current_amc,
                    "plan": plan,
                    "option": option,
                    "latest_nav": nav_val,
                    "nav_date": d_str.strip()
                })
            except Exception as e:
                pass
                
    return records


def fetch_historical_nav(scheme_code, force=False):
    """Fetch NAV history for a single scheme from mfapi.in."""
    url = f"{MFAPI_BASE_URL}/{scheme_code}"
    # Cache historical navs for a longer time, e.g. 7 days if not forced
    data, meta = request_with_cache("GET", url, force=force, max_age_days=7, pause=0.5)
    
    if data and isinstance(data, dict):
        hist = data.get("data", [])
        return hist
    return []

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("action", choices=["master", "history", "bulk"], help="Action to perform")
    ap.add_argument("--category", help="Filter for history fetching")
    ap.add_argument("--limit", type=int, help="Max schemes to fetch history for")
    ap.add_argument("--force", action="store_true", help="Bypass API cache")
    args = ap.parse_args()

    if args.action == "master":
        content = fetch_amfi_nav_master(force=args.force)
        if not content:
            raise SystemExit("Failed to fetch AMFI NAV master.")
            
        records = parse_amfi_nav_master(content)
        if not records:
            raise SystemExit("Failed to parse any records from AMFI NAV master.")
            
        df = pd.DataFrame(records)
        out_file = PROCESSED_DIR / "nav_master.csv"
        df.to_csv(out_file, index=False)
        logging.info(f"Saved {len(df)} schemes to {out_file}")
        
    elif args.action == "history":
        master_file = PROCESSED_DIR / "nav_master.csv"
        if not master_file.exists():
            raise SystemExit(f"Run 'master' action first. {master_file} not found.")
            
        df_master = pd.read_csv(master_file)
        
        if args.category:
            df_master = df_master[df_master['category'].str.contains(args.category, case=False, na=False)]
            
        # Prioritize Growth/Direct plans for history if we are limiting
        df_master = df_master.sort_values(by=["plan", "option"], ascending=[True, True])
        
        if args.limit:
            df_master = df_master.head(args.limit)
            
        logging.info(f"Fetching history for {len(df_master)} schemes...")
        
        hist_records = []
        count = 0
        for _, row in df_master.iterrows():
            code = row['scheme_code']
            hist = fetch_historical_nav(code, force=args.force)
            if hist:
                for entry in hist:
                    hist_records.append({
                        "scheme_code": code,
                        "date": entry.get("date"),
                        "nav": entry.get("nav")
                    })
            count += 1
            if count % 100 == 0:
                logging.info(f"  Processed {count}/{len(df_master)} schemes")
                
        if hist_records:
            df_hist = pd.DataFrame(hist_records)
            # Format dates nicely to YYYY-MM-DD
            df_hist['date'] = pd.to_datetime(df_hist['date'], format='%d-%m-%Y', errors='coerce').dt.strftime('%Y-%m-%d')
            df_hist = df_hist.dropna(subset=['date'])
            df_hist['nav'] = pd.to_numeric(df_hist['nav'], errors='coerce')
            
            # Load existing if exists
            out_file = PROCESSED_DIR / "nav_history.parquet"
            if out_file.exists():
                existing = pd.read_parquet(out_file)
                df_hist = pd.concat([existing, df_hist]).drop_duplicates(subset=["scheme_code", "date"], keep="last")
                
            df_hist.to_parquet(out_file, index=False)
            logging.info(f"Saved {len(df_hist)} historical NAV records to {out_file}")
        else:
            logging.warning("No historical NAV records fetched.")
            
    elif args.action == "bulk":
        # Check local samples first
        local_sample = ROOT / "data" / "samples" / "mutual_fund_data.csv"
        if local_sample.exists():
            logging.info(f"Found local bulk data: {local_sample}")
            df = pd.read_csv(local_sample)
            # Map headers if needed
            logging.info(f"Loaded {len(df)} rows from bulk sample.")
            # For this exercise, we are treating this as an alternative master. 
            # Not fully implementing TigZig crawler as we lack real credentials/endpoints.

if __name__ == "__main__":
    main()
