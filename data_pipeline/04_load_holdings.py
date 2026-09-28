"""04_load_holdings.py - Process AMC portfolio-disclosure files."""

import argparse
import logging
import re
from pathlib import Path
import pandas as pd

from data_pipeline.config import HOLDINGS_RAW_DIR, PROCESSED_DIR

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')


def find_header(raw):
    """Find the row that looks like a header (contains ISIN and something else)."""
    for i in range(min(len(raw), 40)):
        row_str = " ".join(str(x).lower() for x in raw.iloc[i].tolist())
        if "isin" in row_str and ("nav" in row_str or "%" in row_str or "net assets" in row_str):
            return i
    return None

def parse_sheet(raw):
    """Parse a single pandas sheet into a normalized dataframe."""
    h = find_header(raw)
    if h is None:
        return None
        
    df = raw.iloc[h + 1:].copy()
    df.columns = [str(c).strip().lower() for c in raw.iloc[h].tolist()]
    
    # Heuristic column finding
    isin_col = next((c for c in df.columns if "isin" in c), None)
    name_col = next((c for c in df.columns if "instrument" in c or "security" in c or "name" in c), None)
    wt_col = next((c for c in df.columns if "nav" in c or "net assets" in c or c.startswith("%")), None)
    sec_col = next((c for c in df.columns if "industry" in c or "sector" in c or "rating" in c), None)
    
    if not (isin_col and name_col and wt_col):
        return None
        
    out = pd.DataFrame({
        "isin": df[isin_col].astype(str).str.strip(),
        "stock": df[name_col].astype(str).str.strip(),
        "weight": pd.to_numeric(df[wt_col], errors="coerce"),
        "sector": df[sec_col].astype(str).str.strip() if sec_col else ""
    })
    
    # Filter for valid equity ISINs and weights
    out = out[out["isin"].str.match(r"^[A-Z]{2}[0-9A-Z]{10}$", na=False) & out["weight"].notna()]
    
    if not out.empty and out["weight"].max() <= 1.0:
        out["weight"] *= 100
        
    return out

def process_file(file_path):
    key = re.sub(r"[^a-z0-9]+", "_", file_path.stem.lower()).strip("_")
    logging.info(f"Processing {file_path.name} as fund_key '{key}'...")
    
    try:
        if file_path.suffix.lower() == ".csv":
            sheets = {"csv": pd.read_csv(file_path, header=None)}
        else:
            sheets = pd.read_excel(file_path, sheet_name=None, header=None)
    except Exception as e:
        logging.error(f"Cannot read {file_path.name}: {e}")
        return None
        
    for sname, raw in sheets.items():
        parsed = parse_sheet(raw)
        if parsed is not None and not parsed.empty:
            parsed = parsed.groupby(["isin", "stock", "sector"], as_index=False)["weight"].sum()
            parsed.insert(0, "fund_key", key)
            parsed["source"] = file_path.name
            logging.info(f"  -> Extracted {len(parsed)} equity holdings ({parsed.weight.sum():.1f}% NAV)")
            return parsed
            
    logging.warning(f"  -> No equity holdings detected in {file_path.name}.")
    return None

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dir", default=str(HOLDINGS_RAW_DIR), help="Directory containing raw AMC holdings files")
    args = ap.parse_args()
    
    target_dir = Path(args.dir)
    if not target_dir.exists():
        logging.error(f"Holdings directory {target_dir} not found.")
        return
        
    files = [p for p in target_dir.iterdir() if p.suffix.lower() in (".xlsx", ".xls", ".csv")]
    if not files:
        logging.warning(f"No holdings files found in {target_dir}. Place AMC portfolio disclosures there.")
        return
        
    frames = []
    for f in files:
        df = process_file(f)
        if df is not None and not df.empty:
            frames.append(df)
            
    if frames:
        out_file = PROCESSED_DIR / "holdings.csv"
        final_df = pd.concat(frames)
        final_df.to_csv(out_file, index=False)
        logging.info(f"Saved total {len(final_df)} holdings rows to {out_file}")
    else:
        logging.info("No holdings data extracted.")

if __name__ == "__main__":
    main()
