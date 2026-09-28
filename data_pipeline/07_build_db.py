"""07_build_db.py - Build local SQLite market.db from processed datasets."""

import sqlite3
import logging
from pathlib import Path
import pandas as pd

from data_pipeline.config import PROCESSED_DIR, DB_PATH

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')

def create_indexes(conn):
    """Create indexes for faster lookup by agents."""
    commands = [
        "CREATE INDEX IF NOT EXISTS idx_ter_name ON ter(scheme_name)",
        "CREATE INDEX IF NOT EXISTS idx_nav_code ON nav_master(scheme_code)",
        "CREATE INDEX IF NOT EXISTS idx_hist_code_date ON nav_history(scheme_code, date)",
        "CREATE INDEX IF NOT EXISTS idx_tri_index_date ON tri(index_name, date)",
        "CREATE INDEX IF NOT EXISTS idx_holdings_key ON holdings(fund_key)"
    ]
    cur = conn.cursor()
    for cmd in commands:
        try:
            cur.execute(cmd)
        except sqlite3.OperationalError:
            pass # Index might already exist or table missing
    conn.commit()

def load_csv_to_db(conn, file_path, table_name, **read_kwargs):
    if not file_path.exists():
        logging.warning(f"File {file_path.name} not found. Skipping table {table_name}.")
        return False
        
    try:
        df = pd.read_csv(file_path, **read_kwargs)
        df.to_sql(table_name, conn, if_exists="replace", index=False)
        logging.info(f"Loaded {len(df)} rows into {table_name}")
        return True
    except Exception as e:
        logging.error(f"Failed to load {table_name}: {e}")
        return False

def load_parquet_to_db(conn, file_path, table_name, **read_kwargs):
    if not file_path.exists():
        logging.warning(f"File {file_path.name} not found. Skipping table {table_name}.")
        return False
        
    try:
        df = pd.read_parquet(file_path, **read_kwargs)
        df.to_sql(table_name, conn, if_exists="replace", index=False)
        logging.info(f"Loaded {len(df)} rows into {table_name}")
        return True
    except Exception as e:
        logging.error(f"Failed to load {table_name}: {e}")
        return False

def build_db():
    logging.info(f"Building {DB_PATH.name}...")
    
    # Ensure DB directory exists
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    
    with sqlite3.connect(DB_PATH) as conn:
        # Load datasets
        load_csv_to_db(conn, PROCESSED_DIR / "ter.csv", "ter")
        load_csv_to_db(conn, PROCESSED_DIR / "tri.csv", "tri")
        load_csv_to_db(conn, PROCESSED_DIR / "nav_master.csv", "nav_master")
        load_parquet_to_db(conn, PROCESSED_DIR / "nav_history.parquet", "nav_history")
        load_csv_to_db(conn, PROCESSED_DIR / "holdings.csv", "holdings")
        
        # Load peer_stats if it exists
        load_csv_to_db(conn, PROCESSED_DIR / "peer_stats.csv", "peer_stats")
        
        create_indexes(conn)
        
    logging.info("Database build complete.")
    
def main():
    build_db()

if __name__ == "__main__":
    main()
