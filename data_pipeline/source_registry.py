"""Source Registry for Portfolio Surgeon Data Pipeline.

Catalogues all external and internal data sources, file paths, endpoints,
refresh frequencies, schemas, and fallback strategies.
"""

from typing import Dict, Any

SOURCE_REGISTRY: Dict[str, Dict[str, Any]] = {
    "ter_excel": {
        "name": "TER Excel Files (AMFI/NSDL)",
        "description": "Total Expense Ratio data for Mutual Fund Schemes across Direct and Regular plans",
        "local_paths": [
            "ter-of-mf-schemes (1).xlsx",
            "ter-of-mf-schemes.xlsx"
        ],
        "type": "file",
        "format": "xlsx",
        "sheet": "TER_Revised",
        "primary_key": ["NSDL Scheme Code", "TER Date"],
        "schema": {
            "NSDL Scheme Code": "string",
            "Scheme Name": "string",
            "Scheme Type": "string",
            "Scheme Category": "string",
            "TER Date": "datetime",
            "Regular Plan - Total TER (%)": "float",
            "Direct Plan - Total TER (%)": "float"
        },
        "update_frequency": "Monthly",
        "fallback": "data/samples/comprehensive_mutual_funds_data.csv"
    },
    "amfi_nav_daily": {
        "name": "AMFI Daily NAV Feed",
        "description": "Daily Net Asset Value (NAV) for all Indian Mutual Fund schemes from AMFI portal",
        "url": "https://portal.amfiindia.com/spages/NAVAll.txt",
        "fallback_url": "https://www.amfiindia.com/spages/NAVAll.txt",
        "type": "http",
        "format": "semicolon_delimited_text",
        "delimiter": ";",
        "update_frequency": "Daily (Evening)",
        "schema": {
            "Scheme Code": "string",
            "ISIN Div Payout/ Growth": "string",
            "ISIN Div Reinvestment": "string",
            "Scheme Name": "string",
            "Net Asset Value": "float",
            "Date": "date (DD-MMM-YYYY)"
        }
    },
    "mfapi_history": {
        "name": "mfapi.in Scheme History",
        "description": "Historical NAV series for individual schemes via scheme code",
        "url_template": "https://api.mfapi.in/mf/{scheme_code}",
        "type": "http_json",
        "format": "json",
        "update_frequency": "Daily",
        "fallback": "AMFI Daily NAV (Current single-day NAV only)"
    },
    "nifty_tri": {
        "name": "NSE Nifty Total Return Index (TRI)",
        "description": "Historical Nifty Total Return Index data for benchmark CAGR calculations",
        "url": "https://www.niftyindices.com/Backpage.aspx/getTotalReturnIndexString",
        "type": "http_post",
        "format": "json",
        "indices": ["NIFTY 50", "NIFTY 100", "NIFTY 500", "NIFTY MIDCAP 150", "NIFTY SMALLCAP 250", "NIFTY LARGEMIDCAP 250"],
        "update_frequency": "Daily",
        "fallback": "Hardcoded benchmark returns (12% 1Y, 14% 3Y, 13% 5Y)"
    },
    "scheme_master": {
        "name": "Local Scheme Master CSVs",
        "description": "Consolidated metadata for mutual fund schemes including ISINs, AMC, Category, Fund Manager, AUM",
        "local_paths": [
            "data/samples/mutual_fund_data.csv",
            "data/samples/comprehensive_mutual_funds_data.csv"
        ],
        "type": "file",
        "format": "csv",
        "update_frequency": "Static / Periodic",
        "fallback": "Extracted from AMFI NAV feed + TER files"
    },
    "amc_holdings": {
        "name": "AMC Monthly Portfolio Holdings",
        "description": "Stock-level portfolio holdings per mutual fund scheme for overlap analysis",
        "local_dir": "data/raw/holdings",
        "ref_dir": "data_pipeline_ref/data/raw/holdings",
        "type": "dir_xlsx",
        "format": "xlsx/csv",
        "update_frequency": "Monthly",
        "fallback": "Parsed sample AMC sheets or mock portfolio holdings generator"
    }
}


def get_source_info(source_key: str) -> Dict[str, Any]:
    """Retrieve metadata for a specific source."""
    return SOURCE_REGISTRY.get(source_key, {})


def list_all_sources() -> Dict[str, Dict[str, Any]]:
    """Retrieve full registry of sources."""
    return SOURCE_REGISTRY
