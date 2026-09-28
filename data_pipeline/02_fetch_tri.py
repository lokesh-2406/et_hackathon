"""02_fetch_tri.py - Fetch NSE Total Return Index (or Price Return Fallback)."""

import argparse
import logging
from datetime import date, datetime
import pandas as pd
import yfinance as yf

from data_pipeline.config import PROCESSED_DIR

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')

# Yahoo Finance mapping
YF_MAPPING = {
    "NIFTY 50": "^NSEI",
    "NIFTY 100": "^CNX100",
    "NIFTY 500": "^CRSLDX",
    "NIFTY MIDCAP 150": "^NSEMDCP50",
    "NIFTY SMALLCAP 250": "^CNXSC",
    "NIFTY LARGEMIDCAP 250": "^NSEI" # fallback
}

def fetch_yf_index(name, start, end):
    ticker = YF_MAPPING.get(name)
    if not ticker:
        logging.warning(f"No Yahoo Finance mapping for {name}")
        return pd.DataFrame()
        
    logging.info(f"Fetching {name} ({ticker}) via yfinance from {start} to {end}...")
    try:
        # yfinance expects YYYY-MM-DD
        start_fmt = pd.to_datetime(start).strftime("%Y-%m-%d")
        end_fmt = pd.to_datetime(end).strftime("%Y-%m-%d")
        df = yf.download(ticker, start=start_fmt, end=end_fmt, progress=False)
        
        if df.empty:
            return pd.DataFrame()
            
        df = df.reset_index()
        # the structure might have MultiIndex columns if multiple tickers, but we passed a single one.
        # usually columns: Date, Open, High, Low, Close, Adj Close, Volume
        
        # In newer yfinance versions, df.columns might be MultiIndex like ('Close', '^NSEI')
        if isinstance(df.columns, pd.MultiIndex):
            # Flatten or just access the specific level
            close_col = [c for c in df.columns if c[0].lower() == 'close' or c[0].lower() == 'adj close']
            if not close_col:
                close_col = [c for c in df.columns if 'close' in str(c).lower()]
            if close_col:
                val_col = df[close_col[-1]]
            else:
                return pd.DataFrame()
        else:
            val_col = df['Adj Close'] if 'Adj Close' in df.columns else df['Close']
            
        date_col = df['Date'] if 'Date' in df.columns else df.index
        
        out = pd.DataFrame({
            "index_name": name,
            "date": pd.to_datetime(date_col).dt.strftime('%Y-%m-%d'),
            "tri": pd.to_numeric(val_col, errors="coerce"),
            "source": "Yahoo Finance (PR fallback)",
            "retrieved_at": datetime.now().isoformat()
        }).dropna()
        
        return out.sort_values("date")
    except Exception as e:
        logging.error(f"yfinance error for {name}: {e}")
        return pd.DataFrame()

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--start", default="2010-01-01")
    ap.add_argument("--end", default=date.today().strftime("%Y-%m-%d"))
    ap.add_argument("--indices", nargs="*", default=["NIFTY 50", "NIFTY 100", "NIFTY 500", "NIFTY MIDCAP 150", "NIFTY SMALLCAP 250"])
    ap.add_argument("--force", action="store_true")
    args = ap.parse_args()

    frames = []
    
    out_file = PROCESSED_DIR / "tri.csv"
    existing_df = pd.DataFrame()
    if out_file.exists() and not args.force:
        try:
            existing_df = pd.read_csv(out_file)
        except Exception:
            pass

    for name in args.indices:
        f = fetch_yf_index(name, args.start, args.end)
        if not f.empty:
            logging.info(f"{name:<24} {len(f):>5} rows retrieved.")
            frames.append(f)
            
    if not frames and existing_df.empty:
        logging.warning("No TRI data available at all. Creating empty fallback to prevent db build crash.")
        pd.DataFrame(columns=["index_name", "date", "tri", "source", "retrieved_at"]).to_csv(out_file, index=False)
        return
        
    if frames:
        new_df = pd.concat(frames)
        if not existing_df.empty:
            df = pd.concat([existing_df, new_df]).drop_duplicates(subset=["index_name", "date"], keep="last")
        else:
            df = new_df
            
        df = df.sort_values(["index_name", "date"])
        df.to_csv(out_file, index=False)
        logging.info(f"Saved {len(df)} total TRI rows -> {out_file}")

if __name__ == "__main__":
    main()
