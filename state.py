from typing import TypedDict, List, Dict, Any, Optional


class PortfolioState(TypedDict):
    # Input
    pdf_path: str
    user_age: Optional[int]
    monthly_sip: Optional[float]

    # Parser output
    folios: List[Dict]          # [{scheme, isin, date, amt, units, nav}]
    parse_errors: List[str]

    # Enrichment
    nav_history: Dict[str, List]        # isin -> [{date, nav}]
    benchmark_returns: Dict             # {1y, 3y, 5y} nifty50 returns
    fund_holdings: Dict[str, List]      # isin -> top10 holdings

    # Diagnostician output
    diagnostics: Dict[str, Any]
    health_score: float

    # Debate Club output
    verdicts: List[Dict]                # [{fund, bull, bear, verdict, score}]

    # Strategist output
    rebalancing_plan: Dict
    glide_path: List[Dict]

    # Executor output
    action_memo: str

    # Monitor output
    watchlist: List[Dict]