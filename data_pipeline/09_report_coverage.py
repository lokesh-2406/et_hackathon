"""09_report_coverage.py - Generate data quality and coverage reports."""

import sqlite3
import pandas as pd
from pathlib import Path
from data_pipeline.config import DB_PATH, DATA_DIR

def main():
    if not DB_PATH.exists():
        print(f"Database {DB_PATH} does not exist. Cannot generate report.")
        return
        
    with sqlite3.connect(DB_PATH) as conn:
        print("Generating data coverage report...")
        
        # We start with the NAV master as the universe of known schemes
        try:
            master_df = pd.read_sql("SELECT scheme_code, scheme_name, category, plan FROM nav_master", conn)
        except Exception as e:
            print(f"Failed to read nav_master: {e}")
            return
            
        try:
            ter_df = pd.read_sql("SELECT scheme_code_if_available, 1 as has_ter FROM ter WHERE scheme_code_if_available IS NOT NULL", conn)
            # Try matching by name as a fallback if scheme code wasn't joined
            ter_names = pd.read_sql("SELECT scheme_name, 1 as has_ter_by_name FROM ter", conn)
        except Exception:
            ter_df = pd.DataFrame(columns=["scheme_code_if_available", "has_ter"])
            ter_names = pd.DataFrame(columns=["scheme_name", "has_ter_by_name"])
            
        try:
            nav_hist_df = pd.read_sql("""
                SELECT scheme_code, 1 as has_nav, MIN(date) as nav_start, MAX(date) as nav_end, COUNT(*) as nav_days 
                FROM nav_history GROUP BY scheme_code
            """, conn)
        except Exception:
            nav_hist_df = pd.DataFrame(columns=["scheme_code", "has_nav", "nav_start", "nav_end", "nav_days"])
            
        try:
            peer_df = pd.read_sql("SELECT scheme_code, 1 as has_peer_stats FROM peer_stats", conn)
        except Exception:
            peer_df = pd.DataFrame(columns=["scheme_code", "has_peer_stats"])
            
        # Merge it all together
        coverage = master_df.merge(nav_hist_df, on="scheme_code", how="left")
        coverage = coverage.merge(peer_df, on="scheme_code", how="left")
        
        # Merge TER by code, then fallback to name
        if not ter_df.empty:
            ter_df["scheme_code_if_available"] = pd.to_numeric(ter_df["scheme_code_if_available"], errors="coerce")
            coverage = coverage.merge(ter_df, left_on="scheme_code", right_on="scheme_code_if_available", how="left")
            coverage = coverage.drop(columns=["scheme_code_if_available"])
        else:
            coverage["has_ter"] = None
            
        if not ter_names.empty:
            coverage = coverage.merge(ter_names, on="scheme_name", how="left")
            coverage["has_ter"] = coverage["has_ter"].fillna(coverage["has_ter_by_name"])
            coverage = coverage.drop(columns=["has_ter_by_name"])
            
        # Fill NAs for boolean flags
        for col in ["has_ter", "has_nav", "has_peer_stats"]:
            if col in coverage.columns:
                coverage[col] = coverage[col].fillna(0).astype(bool)
                
        out_csv = DATA_DIR / "fund_data_coverage.csv"
        coverage.to_csv(out_csv, index=False)
        print(f"Coverage report generated: {out_csv}")
        
        # Print summary
        print("\n--- Data Coverage Summary ---")
        print(f"Total known schemes: {len(coverage)}")
        print(f"Schemes with TER: {coverage.get('has_ter', pd.Series()).sum()}")
        print(f"Schemes with NAV history: {coverage.get('has_nav', pd.Series()).sum()}")
        print(f"Schemes with Peer Stats: {coverage.get('has_peer_stats', pd.Series()).sum()}")
        print("-----------------------------\n")

if __name__ == "__main__":
    main()
