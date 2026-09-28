"""02_fetch_tri.py - Fetch NSE Total Return Index History."""

import argparse
import json
import logging
from datetime import date, datetime
import pandas as pd
import requests

from data_pipeline.config import NIFTY_TRI_URL, NIFTY_REFERER, TRI_INDICES, PROCESSED_DIR, USER_AGENT
from data_pipeline.http_util import request_with_cache, read_cache, write_cache

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')

def fetch_index_with_session(session, name, start, end, force=False):
    """
    NSE expects single-quoted pseudo-JSON inside the string.
    We need to handle the session manually to bootstrap cookies for NSE,
    so we use requests.Session() and manual cache handling here instead of the generic wrapper.
    """
    payload = {"cinfo": "{'name':'%s','startDate':'%s','endDate':'%s','indexName':'%s'}" 
               % (name, start, end, name)}
               
    if not force:
        cached = read_cache(NIFTY_TRI_URL, "POST", data=payload, max_age_days=1)
        if cached:
            inner = cached.get("content", {}).get("d", "[]")
            return json.loads(inner) if isinstance(inner, str) else inner

    logging.info(f"Fetching {name} from {start} to {end}...")
    headers = {
        **USER_AGENT,
        "Content-Type": "application/json; charset=UTF-8",
        "X-Requested-With": "XMLHttpRequest", 
        "Referer": NIFTY_REFERER
    }
    
    r = session.post(NIFTY_TRI_URL, json=payload, timeout=60, headers=headers)
    r.raise_for_status()
    
    # Cache it
    write_cache(NIFTY_TRI_URL, "POST", None, payload, r.text, r.status_code, dict(r.headers))
    
    inner = r.json().get("d", "[]")
    return json.loads(inner) if isinstance(inner, str) else inner

def normalize_tri_data(name, recs):
    """Normalize the heuristic fields from NSE response."""
    if not recs:
        return pd.DataFrame()
        
    df = pd.DataFrame(recs)
    
    # Heuristic column detection (often changes)
    date_col = next((c for c in df.columns if "date" in c.lower()), None)
    val_col = next((c for c in df.columns if c != date_col and 
                   ("total" in c.lower() or "tri" in c.lower() or 
                    "close" in c.lower() or "index" in c.lower())), None)
                    
    if not date_col or not val_col:
        logging.warning(f"Could not detect date/val cols for {name}. Cols: {df.columns.tolist()}")
        return pd.DataFrame()
        
    out = pd.DataFrame({
        "index_name": name,
        "date": pd.to_datetime(df[date_col], dayfirst=True, errors="coerce").dt.strftime('%Y-%m-%d'),
        "tri": pd.to_numeric(df[val_col].astype(str).str.replace(",", ""), errors="coerce"),
        "source": "NSE",
        "retrieved_at": datetime.now().isoformat()
    }).dropna()
    
    return out.sort_values("date")

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--start", default="01-Jan-2010")
    ap.add_argument("--end", default=date.today().strftime("%d-%b-%Y"))
    ap.add_argument("--indices", nargs="*", default=TRI_INDICES)
    ap.add_argument("--force", action="store_true")
    args = ap.parse_args()

    # Bootstrap NSE session
    s = requests.Session()
    s.headers.update(USER_AGENT)
    try:
        s.get(NIFTY_REFERER, timeout=30)
    except Exception as e:
        logging.warning(f"Failed to bootstrap NSE session cookies: {e}")

    frames = []
    
    # Ensure existing data is loaded if we want to merge/incremental (Optional extension)
    out_file = PROCESSED_DIR / "tri.csv"
    existing_df = pd.DataFrame()
    if out_file.exists() and not args.force:
        try:
            existing_df = pd.read_csv(out_file)
            logging.info(f"Loaded {len(existing_df)} existing TRI rows.")
        except Exception:
            pass

    for name in args.indices:
        try:
            recs = fetch_index_with_session(s, name, args.start, args.end, force=args.force)
            if recs:
                logging.info(f"{name:<24} {len(recs):>5} rows retrieved.")
                f = normalize_tri_data(name, recs)
                if not f.empty:
                    frames.append(f)
        except Exception as e:
            logging.error(f"{name:<24} FAILED: {type(e).__name__}: {e}")
            
    if not frames and existing_df.empty:
        raise SystemExit("No TRI data available at all.")
        
    if frames:
        new_df = pd.concat(frames)
        if not existing_df.empty:
            df = pd.concat([existing_df, new_df]).drop_duplicates(subset=["index_name", "date"], keep="last")
        else:
            df = new_df
            
        df = df.sort_values(["index_name", "date"])
        df.to_csv(out_file, index=False)
        logging.info(f"Saved {len(df)} total TRI rows -> {out_file}")
    else:
        logging.info("No new frames added, retaining existing TRI data.")

if __name__ == "__main__":
    main()
