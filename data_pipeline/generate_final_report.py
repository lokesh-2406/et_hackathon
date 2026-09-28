"""generate_final_report.py - Prints the final data extraction summary."""

import sqlite3
import pandas as pd
from pathlib import Path
from data_pipeline.config import DB_PATH, DATA_DIR

def run_report():
    if not DB_PATH.exists():
        print("Database not found!")
        return

    report = []
    def add(msg=""): report.append(msg)

    with sqlite3.connect(DB_PATH) as conn:
        add("================================================")
        add("DATA EXTRACTION SUMMARY")
        add("================================================\n")
        
        try:
            ter_rows = pd.read_sql("SELECT COUNT(*) as c FROM ter", conn).iloc[0]['c']
            ter_schemes = pd.read_sql("SELECT COUNT(DISTINCT scheme_name) as c FROM ter", conn).iloc[0]['c']
            ter_amcs = pd.read_sql("SELECT COUNT(DISTINCT amc) as c FROM ter", conn).iloc[0]['c']
            ter_dates = pd.read_sql("SELECT MIN(month) as m1, MAX(month) as m2 FROM ter", conn).iloc[0]
            ter_src = pd.read_sql("SELECT source FROM ter LIMIT 1", conn).iloc[0]['source'] if ter_rows else "N/A"
            add("TER:")
            add(f"rows: {ter_rows}")
            add(f"schemes: {ter_schemes}")
            add(f"AMCs: {ter_amcs}")
            add(f"earliest: {ter_dates['m1']}")
            add(f"latest: {ter_dates['m2']}")
            add(f"source: {ter_src}\n")
        except Exception:
            add("TER: ERROR\n")

        try:
            tri_rows = pd.read_sql("SELECT COUNT(*) as c FROM tri", conn).iloc[0]['c']
            tri_idx = pd.read_sql("SELECT COUNT(DISTINCT index_name) as c FROM tri", conn).iloc[0]['c']
            tri_dates = pd.read_sql("SELECT MIN(date) as m1, MAX(date) as m2 FROM tri", conn).iloc[0]
            add("TRI:")
            add(f"indices: {tri_idx}")
            add(f"rows: {tri_rows}")
            add(f"earliest: {tri_dates['m1']}")
            add(f"latest: {tri_dates['m2']}\n")
        except Exception:
            add("TRI: ERROR\n")

        try:
            mst_rows = pd.read_sql("SELECT COUNT(*) as c FROM nav_master", conn).iloc[0]['c']
            mst_amcs = pd.read_sql("SELECT COUNT(DISTINCT amc) as c FROM nav_master", conn).iloc[0]['c']
            mst_cat = pd.read_sql("SELECT COUNT(DISTINCT category) as c FROM nav_master", conn).iloc[0]['c']
            add("SCHEME MASTER:")
            add(f"schemes: {mst_rows}")
            add(f"AMCs: {mst_amcs}")
            add(f"categories: {mst_cat}\n")
        except Exception:
            add("SCHEME MASTER: ERROR\n")

        try:
            nav_rows = pd.read_sql("SELECT COUNT(*) as c FROM nav_history", conn).iloc[0]['c']
            nav_sc = pd.read_sql("SELECT COUNT(DISTINCT scheme_code) as c FROM nav_history", conn).iloc[0]['c']
            nav_dates = pd.read_sql("SELECT MIN(date) as m1, MAX(date) as m2 FROM nav_history", conn).iloc[0]
            add("NAV HISTORY:")
            add(f"rows: {nav_rows}")
            add(f"schemes: {nav_sc}")
            add(f"earliest: {nav_dates['m1']}")
            add(f"latest: {nav_dates['m2']}\n")
        except Exception:
            add("NAV HISTORY: ERROR\n")

        try:
            hol_funds = pd.read_sql("SELECT COUNT(DISTINCT fund_key) as c FROM holdings", conn).iloc[0]['c']
            hol_sec = pd.read_sql("SELECT COUNT(DISTINCT isin) as c FROM holdings", conn).iloc[0]['c']
            add("HOLDINGS:")
            add(f"funds: {hol_funds}")
            add(f"securities: {hol_sec}")
            add("earliest: N/A")
            add("latest: N/A\n")
        except Exception:
            add("HOLDINGS: ERROR\n")

        try:
            peer_sc = pd.read_sql("SELECT COUNT(*) as c FROM peer_stats", conn).iloc[0]['c']
            peer_cat = pd.read_sql("SELECT COUNT(DISTINCT category) as c FROM peer_stats", conn).iloc[0]['c']
            add("PEER STATS:")
            add(f"schemes: {peer_sc}")
            add(f"categories: {peer_cat}\n")
        except Exception:
            add("PEER STATS: ERROR\n")
            
        add("AMFI INDUSTRY DATA: UNAVAILABLE")
        add("FACTSHEETS: UNAVAILABLE")
        add("NEWS: UNAVAILABLE")
        add("MACRO: UNAVAILABLE\n")
        
        add("================================================")
        add("DATABASE")
        add("================================================")
        tables = pd.read_sql("SELECT name FROM sqlite_master WHERE type='table'", conn)
        for t in tables['name']:
            rc = pd.read_sql(f"SELECT COUNT(*) as c FROM {t}", conn).iloc[0]['c']
            add(f"Table {t}: {rc} rows")
            
    reports_dir = DATA_DIR / "reports"
    reports_dir.mkdir(exist_ok=True)
    report_file = reports_dir / "final_data_report.txt"
    with open(report_file, "w") as f:
        f.write("\n".join(report))
        
    print("\n".join(report))

if __name__ == "__main__":
    run_report()
