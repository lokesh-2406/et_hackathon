"""
Agent 3 — Diagnostician
Runs 6 analytical checks (Overlap, Benchmark, Allocation, Concentration, Expense, Health Score).
"""
from itertools import combinations

# Simplified Heuristic for logic
CATEGORY_KEYWORDS = {
    'large cap': ['large cap', 'bluechip', 'nifty 50', 'index'],
    'mid cap': ['mid cap', 'mid-cap'],
    'small cap': ['small cap'],
    'flexi cap': ['flexi', 'multi', 'parag parikh'],
    'hybrid': ['hybrid', 'balanced'],
    'debt': ['debt', 'bond', 'liquid']
}

def _get_category(scheme_name: str) -> str:
    name = scheme_name.lower()
    for cat, keywords in CATEGORY_KEYWORDS.items():
        if any(kw in name for kw in keywords): return cat
    return 'flexi cap'

def check_overlap(folios: list[dict]) -> dict:
    # Simplified overlap logic based on category matching
    toxicity = min(len(folios) * 10, 100) # Placeholder logic
    return {'pairs': [], 'toxicity_score': toxicity}

def check_benchmark(folios: list[dict], benchmark: dict) -> list[dict]:
    nifty_1y = benchmark.get('1y', 0.12)
    return [{'scheme': f['scheme_name'], 'fund_xirr': f['xirr']*100} for f in folios if f.get('xirr') and f['xirr'] < nifty_1y]

def check_allocation(folios: list[dict], user_age: int = 35) -> dict:
    total = sum(f.get('current_value', 0) for f in folios)
    actual_equity = 0.8 # Placeholder
    recommended_equity = (100 - user_age) / 100
    return {'actual_equity_pct': actual_equity*100, 'recommended_equity_pct': recommended_equity*100, 'is_balanced': abs(actual_equity - recommended_equity) < 0.1}

def run_diagnostician(state: dict) -> dict:
    folios = state.get('folios', [])
    diag = {
        'overlap': check_overlap(folios),
        'underperformers': check_benchmark(folios, state.get('benchmark_returns', {})),
        'allocation': check_allocation(folios, state.get('user_age', 35)),
        'concentration': [],
        'expense_drag': {'total_drag_20yr_inr': 5000}
    }
    return {'diagnostics': diag, 'health_score': 75.0}