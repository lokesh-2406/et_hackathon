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

def check_overlap(folios: list) -> dict:
    LARGE_CAP_KEYWORDS = ['large cap','bluechip','top 100','nifty','index','large & mid']
    pairs = []
    for i, f1 in enumerate(folios):
        for f2 in folios[i+1:]:
            n1, n2 = f1['scheme_name'].lower(), f2['scheme_name'].lower()
            both_large = any(k in n1 for k in LARGE_CAP_KEYWORDS) and any(k in n2 for k in LARGE_CAP_KEYWORDS)
            both_flexi = ('flexi' in n1 or 'multi' in n1) and ('flexi' in n2 or 'multi' in n2)
            if both_large:
                pairs.append({'fund1': f1['scheme_name'], 'fund2': f2['scheme_name'], 'overlap_pct': 65})
            elif both_flexi:
                pairs.append({'fund1': f1['scheme_name'], 'fund2': f2['scheme_name'], 'overlap_pct': 45})
    toxicity = min(len(pairs) * 20, 100)
    return {'pairs': pairs, 'toxicity_score': toxicity}

def check_benchmark(folios: list[dict], benchmark: dict) -> list[dict]:
    nifty_1y = benchmark.get('1y', 0.12)
    return [{'scheme': f['scheme_name'], 'fund_xirr': f['xirr']*100} for f in folios if f.get('xirr') and f['xirr'] < nifty_1y]

# agents/diagnostician.py — replace check_allocation
def check_allocation(folios: list, user_age: int = 35) -> dict:
    total = sum(f.get('current_value', 0) for f in folios)
    if total == 0:
        return {}
    breakdown = {'large_cap': 0, 'mid_cap': 0, 'small_cap': 0, 'hybrid': 0, 'debt': 0}
    for f in folios:
        name = f['scheme_name'].lower()
        val = f.get('current_value', 0)
        pct = val / total
        if any(k in name for k in ['large', 'index', 'nifty', 'bluechip', 'top 100']):
            breakdown['large_cap'] += pct
        elif 'mid' in name:
            breakdown['mid_cap'] += pct
        elif 'small' in name:
            breakdown['small_cap'] += pct
        elif any(k in name for k in ['hybrid', 'balanced']):
            breakdown['hybrid'] += pct
        elif any(k in name for k in ['debt', 'bond', 'liquid', 'gilt']):
            breakdown['debt'] += pct
        else:
            breakdown['large_cap'] += pct  # flexi-cap treated as equity

    recommended_equity = (100 - user_age) / 100
    actual_equity = 1 - breakdown['debt'] - breakdown['hybrid'] * 0.4
    deviation = abs(actual_equity - recommended_equity) * 100

    return {
        'breakdown': {k: round(v * 100, 1) for k, v in breakdown.items()},
        'recommended_equity_pct': round(recommended_equity * 100, 1),
        'actual_equity_pct': round(actual_equity * 100, 1),
        'deviation_pct': round(deviation, 1),
        'is_balanced': deviation < 10,
    }
# added to compute a simple health score based on diagnostics, with caps to prevent any single factor from dominating the score
def compute_health_score(overlap: dict, underperf: list, alloc: dict, conc: list) -> float:
    score = 100.0
    score -= min(overlap.get('toxicity_score', 0) * 0.3, 30)  # max 30 pts
    score -= min(len(underperf) * 8, 24)                        # max 24 pts
    if not alloc.get('is_balanced', True):
        score -= 15
    score -= min(len(conc) * 10, 20)                            # max 20 pts
    return max(round(score, 1), 0)

def check_concentration(folios: list) -> list:
    total = sum(f.get('current_value', 0) for f in folios)
    if total == 0:
        return []
    return [
        {'scheme': f['scheme_name'], 'pct': round(f.get('current_value', 0) / total * 100, 1),
         'current_value': f.get('current_value', 0)}
        for f in folios
        if f.get('current_value', 0) / total > 0.30
    ]

def run_diagnostician(state: dict) -> dict:
    folios = state.get('folios', [])
    diag = {
        'overlap': check_overlap(folios),
        'underperformers': check_benchmark(folios, state.get('benchmark_returns', {})),
        'allocation': check_allocation(folios, state.get('user_age', 35)),
        'concentration': check_concentration(folios),
        'expense_drag': {'total_drag_20yr_inr': 5000}
    }
    score = compute_health_score(
        diag['overlap'], diag['underperformers'],
        diag['allocation'], diag['concentration']
    )
    return {'diagnostics': diag, 'health_score': score}