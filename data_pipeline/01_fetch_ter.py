"""01_fetch_ter.py - Fetch Total Expense Ratio data from AMFI or Local XLSX Fallbacks."""

import argparse
import json
import logging
from datetime import date, datetime
import pandas as pd

from data_pipeline.config import AMFI_API_BASE, PROCESSED_DIR, ROOT
from data_pipeline.http_util import request_with_cache

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')

def prev_months(n=6):
    """Generate YYYY-MM strings backwards from current month."""
    y, m = date.today().year, date.today().month
    for _ in range(n):
        yield f"{m:02d}-{y}"
        m -= 1
        if m == 0:
            m, y = 12, y - 1

def pick(d, *keys):
    for k in keys:
        if k in d and d[k] not in (None, ""):
            return d[k]
    return None

def fetch_amc_list(force=False):
    url = f"{AMFI_API_BASE}/populate-mf"
    data, meta = request_with_cache("GET", url, force=force, max_age_days=7)
    return data if isinstance(data, list) else []

def fetch_ter_for_month(amcs, month, amc_filter=None, force=False):
    rows = []
    for a in amcs:
        mf_id = pick(a, "MF_ID", "mfId", "id", "value", "Id")
        name = str(pick(a, "MF_Name", "name", "label", "Name", "text") or mf_id)
        
        if mf_id is None or (amc_filter and amc_filter.lower() not in name.lower()):
            continue
            
        url = (f"{AMFI_API_BASE}/populate-te-rdata-revised?MF_ID={mf_id}&Month={month}"
               f"&strCat=-1&strType=1&page=1&pageSize=10000")
               
        # We don't cache 404s/empty aggressively, but we do cache successes
        data, meta = request_with_cache("GET", url, force=force, pause=2.0)
        
        if data and isinstance(data, dict):
            got = data.get("data") or []
        elif data and isinstance(data, list):
            got = data
        else:
            got = []
            
        if got:
            logging.info(f"  {name:<40} {len(got):>4} schemes")
            for r in got:
                # Normalize schema on the fly
                rows.append({
                    "scheme_code_if_available": r.get("Scheme_Code") or r.get("schemeCode"),
                    "scheme_name": r.get("Scheme_Name") or r.get("schemeName"),
                    "category": r.get("SchemeCat_Desc") or r.get("schemeCategory"),
                    "amc": name,
                    "regular_ter": pd.to_numeric(r.get("R_TER"), errors="coerce"),
                    "direct_ter": pd.to_numeric(r.get("D_TER"), errors="coerce"),
                    "month": month,
                    "source": "AMFI API",
                    "retrieved_at": datetime.now().isoformat()
                })
    return rows

def fallback_to_local_excel():
    logging.info("Falling back to local XLSX datasets...")
    candidates = [
        ROOT / "ter-of-mf-schemes (1).xlsx",
        ROOT / "ter-of-mf-schemes.xlsx"
    ]
    
    best_df = None
    for cand in candidates:
        if not cand.exists():
            continue
        try:
            df = pd.read_excel(cand, sheet_name="TER_Revised")
            logging.info(f"Loaded {cand.name}: {len(df)} rows.")
            if best_df is None or len(df) > len(best_df):
                best_df = df
        except Exception as e:
            logging.error(f"Error reading {cand.name}: {e}")
            
    if best_df is None or best_df.empty:
        return []
        
    # Map from XLSX columns to canonical schema
    rows = []
    retrieved_at = datetime.now().isoformat()
    for _, r in best_df.iterrows():
        try:
            r_ter = pd.to_numeric(r.get("Regular Plan - Total TER (%)"), errors="coerce")
            d_ter = pd.to_numeric(r.get("Direct Plan - Total TER (%)"), errors="coerce")
            
            # Try to extract AMC from Scheme Name or Scheme Code structure? 
            # Or just leave it blank since AMCs aren't explicitly in the xlsx
            scheme_name = str(r.get("Scheme Name", ""))
            
            # Simple heuristic for AMC: first word of scheme name (often true in India)
            amc_heuristic = scheme_name.split()[0] if scheme_name else "Unknown"
            
            # Date format in Excel is datetime
            ter_date = r.get("TER Date")
            month_str = ter_date.strftime("%m-%Y") if pd.notnull(ter_date) else "Unknown"

            rows.append({
                "scheme_code_if_available": str(r.get("NSDL Scheme Code", "")),
                "scheme_name": scheme_name,
                "category": str(r.get("Scheme Category", "")),
                "amc": amc_heuristic,
                "regular_ter": r_ter,
                "direct_ter": d_ter,
                "month": month_str,
                "source": "Local XLSX Fallback",
                "retrieved_at": retrieved_at
            })
        except Exception:
            continue
            
    return rows

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--month", help="MM-YYYY format")
    ap.add_argument("--amc", help="Filter by AMC name")
    ap.add_argument("--force", action="store_true", help="Bypass API cache")
    args = ap.parse_args()

    rows = []
    used_month = None

    # 1. Try AMFI API
    try:
        amcs = fetch_amc_list(force=args.force)
        if amcs:
            months_to_try = [args.month] if args.month else list(prev_months())
            for m in months_to_try:
                logging.info(f"Trying month {m} via API...")
                api_rows = fetch_ter_for_month(amcs, m, args.amc, force=args.force)
                if api_rows:
                    rows = api_rows
                    used_month = m
                    break
        else:
            logging.warning("AMFI API returned no AMCs.")
    except Exception as e:
        logging.error(f"AMFI API Fetch failed: {e}")

    # 2. Fallback to Local Excel
    if not rows:
        logging.warning("No TER rows returned from API. Using fallback.")
        rows = fallback_to_local_excel()

    if not rows:
        raise SystemExit("No TER data could be extracted from any source.")

    # 3. Normalize and Output
    df = pd.DataFrame(rows)
    
    # Calculate gap
    df["ter_gap"] = df["regular_ter"] - df["direct_ter"]
    
    # Clean up negatives/nans
    df["ter_gap"] = df["ter_gap"].where((df["ter_gap"] > -1) & (df["ter_gap"] < 5), None)
    
    # Sort for consistency
    df = df.sort_values(by=["amc", "scheme_name"]).drop_duplicates(subset=["scheme_name"], keep="last")

    out_file = PROCESSED_DIR / "ter.csv"
    df.to_csv(out_file, index=False)
    logging.info(f"Saved {len(df)} canonical TER records -> {out_file}")

if __name__ == "__main__":
    main()
