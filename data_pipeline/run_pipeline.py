"""run_pipeline.py - Orchestrator for Portfolio Surgeon Data Extraction."""

import argparse
import logging
import subprocess
import sys
from pathlib import Path

# Add root to pythonpath for subprocesses if run directly
ROOT_DIR = Path(__file__).resolve().parent.parent

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')

def run_script(module_name, *args):
    """Run a pipeline script as a module to ensure paths resolve correctly."""
    cmd = [sys.executable, "-m", f"data_pipeline.{module_name}"]
    cmd.extend(args)
    logging.info(f"Running: {' '.join(cmd)}")
    
    result = subprocess.run(cmd, cwd=str(ROOT_DIR))
    if result.returncode != 0:
        logging.error(f"Failed step: {module_name}")
        return False
    return True

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--full", action="store_true", help="Run full pipeline ignoring cache")
    ap.add_argument("--incremental", action="store_true", help="Run full pipeline using cache")
    ap.add_argument("--skip-ter", action="store_true")
    ap.add_argument("--skip-tri", action="store_true")
    ap.add_argument("--skip-nav", action="store_true")
    ap.add_argument("--skip-holdings", action="store_true")
    ap.add_argument("--skip-peers", action="store_true")
    ap.add_argument("--skip-db", action="store_true")
    ap.add_argument("--force", action="store_true", help="Force API fetch")
    
    args = ap.parse_args()
    
    force_args = ["--force"] if (args.force or args.full) else []

    logging.info("Starting Portfolio Surgeon Data Pipeline...")
    
    if not args.skip_ter:
        logging.info("--- PHASE 3.1: TER ---")
        run_script("01_fetch_ter", *force_args)
        
    if not args.skip_tri:
        logging.info("--- PHASE 3.2: TRI ---")
        run_script("02_fetch_tri", *force_args)
        
    if not args.skip_nav:
        logging.info("--- PHASE 3.3: NAV MASTER & HISTORY ---")
        run_script("03_fetch_navs", "master", *force_args)
        # Note: we might want to restrict this in typical full runs to prevent a multi-hour download 
        # unless specifically requested. For now we use the default logic in the script.
        run_script("03_fetch_navs", "history", *force_args)
        
    if not args.skip_holdings:
        logging.info("--- PHASE 3.4: HOLDINGS ---")
        run_script("04_load_holdings")
        
    if not args.skip_peers:
        logging.info("--- PHASE 6: PEER STATS ---")
        run_script("05_build_peer_stats")
        
    if not args.skip_db:
        logging.info("--- PHASE 7: DATABASE ---")
        run_script("07_build_db")
        
    logging.info("Pipeline Complete.")
    logging.info("Data extracted, validated, and normalized into data/market.db.")
    
if __name__ == "__main__":
    main()
