"""
Agent 3 — Diagnostician
Runs 6 analytical checks (Overlap, Benchmark, Allocation, Concentration, Expense, Health Score).
"""
from itertools import combinations

# Simplified Heuristic for logic
CATEGORY_KEYWORDS = {
    'large cap': ['large cap', 'bluechip', 'nifty 50', 'index', 'top 100'],
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
    """
    Detect overlapping fund pairs using category-based heuristics.
    Large-cap funds share ~65% holdings; flexi-cap funds share ~45%.
    Toxicity = min(n_overlapping_pairs * 20, 100).
    """
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

def check_benchmark(folios: list, benchmark: dict) -> list:
    """
    Flag funds whose XIRR is below the Nifty 50 1-year return.
    Returns list with keys: scheme, fund_xirr, nifty_return, underperformance
    (monitor.py needs nifty_return and underperformance).
    """
    nifty_1y = benchmark.get('1y', 0.12)
    result = []
    for f in folios:
        if f.get('xirr') is None:
            continue
        fund_xirr_pct = f['xirr'] * 100
        nifty_pct = nifty_1y * 100
        if f['xirr'] < nifty_1y:
            result.append({
                'scheme':           f['scheme_name'],
                'fund_xirr':        round(fund_xirr_pct, 1),
                'nifty_return':     round(nifty_pct, 1),
                'underperformance': round(nifty_pct - fund_xirr_pct, 1),
            })
    return result

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

def _compute_portfolio_drag(folios: list) -> dict:
    from utils.calculations import compute_expense_drag
    total_10, total_20, total_30 = 0, 0, 0
    for f in folios:
        ter = f.get('real_ter', 0.015)
        val = f.get('current_value', 0)
        drag = compute_expense_drag(ter, val)
        total_10 += drag.get(10, 0)
        total_20 += drag.get(20, 0)
        total_30 += drag.get(30, 0)
    return {'total_drag_10yr_inr': round(total_10), 
            'total_drag_20yr_inr': round(total_20),
            'total_drag_30yr_inr': round(total_30)}

def run_diagnostician(state: dict) -> dict:
    folios = state.get('folios', [])
    diag = {
        'overlap': check_overlap(folios),
        'underperformers': check_benchmark(folios, state.get('benchmark_returns', {})),
        'allocation': check_allocation(folios, state.get('user_age', 35)),
        'concentration': check_concentration(folios),
        'expense_drag': _compute_portfolio_drag(folios)
    }
    score = compute_health_score(
        diag['overlap'], diag['underperformers'],
        diag['allocation'], diag['concentration']
    )
    return {'diagnostics': diag, 'health_score': score}