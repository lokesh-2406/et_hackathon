"""Shared configuration, paths, and constants for Portfolio Surgeon Data Pipeline."""
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# Data directory hierarchy
DATA_DIR = ROOT / "data"
RAW_DIR = DATA_DIR / "raw"
PROCESSED_DIR = DATA_DIR / "processed"
REPORTS_DIR = DATA_DIR / "reports"

HOLDINGS_RAW_DIR = RAW_DIR / "holdings"
NAV_RAW_DIR = RAW_DIR / "nav"
TER_RAW_DIR = RAW_DIR / "ter"

DB_PATH = DATA_DIR / "market.db"

# Create directories if they don't exist
for p in [DATA_DIR, RAW_DIR, PROCESSED_DIR, REPORTS_DIR, HOLDINGS_RAW_DIR, NAV_RAW_DIR, TER_RAW_DIR]:
    p.mkdir(parents=True, exist_ok=True)

USER_AGENT = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
}

# External API URLs
AMFI_API_BASE = "https://www.amfiindia.com/api"
AMFI_NAV_ALL_URL = "https://portal.amfiindia.com/spages/NAVAll.txt"
AMFI_NAV_FALLBACK_URL = "https://www.amfiindia.com/spages/NAVAll.txt"
MFAPI_BASE_URL = "https://api.mfapi.in/mf"

NIFTY_TRI_URL = "https://www.niftyindices.com/Backpage.aspx/getTotalReturnIndexString"
NIFTY_REFERER = "https://www.niftyindices.com/reports/historical-data"

# Nifty Benchmark TRI Indices
TRI_INDICES = [
    "NIFTY 50",
    "NIFTY 100",
    "NIFTY 500",
    "NIFTY MIDCAP 150",
    "NIFTY SMALLCAP 250",
    "NIFTY LARGEMIDCAP 250",
]

# Standard Benchmark mapping by category keywords
CATEGORY_BENCHMARK_MAPPING = [
    ("small cap", "NIFTY SMALLCAP 250"),
    ("mid cap", "NIFTY MIDCAP 150"),
    ("large & mid", "NIFTY LARGEMIDCAP 250"),
    ("large cap", "NIFTY 100"),
    ("flexi cap", "NIFTY 500"),
    ("multi cap", "NIFTY 500"),
    ("elss", "NIFTY 500"),
    ("focused", "NIFTY 500"),
    ("value", "NIFTY 500"),
    ("contra", "NIFTY 500"),
    ("dividend yield", "NIFTY 500"),
    ("index", "NIFTY 50"),
]
DEFAULT_BENCHMARK = "NIFTY 50"

# Financial constants
RISK_FREE_RATE = 0.065  # 6.5% annual risk-free rate for Sharpe ratio calculations
