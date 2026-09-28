"""
Agent 3 — Diagnostician
Runs analytical checks using actual underlying market data.
"""
from utils.market_data import portfolio_overlap, expense_drag, benchmark_for

def check_overlap(folios: list) -> dict:
    """
    Detect overlapping fund pairs using actual holding-level data.
    """
    fund_values = [(f['scheme_name'], f.get('current_value', 0)) for f in folios]
    ov = portfolio_overlap(fund_values)
    
    return {
        'pairs': [{'fund1': p[0], 'fund2': p[1], 'overlap_pct': p[2]} for p in ov.get('pairs', [])],
        'toxicity_score': ov.get('toxicity', 0),
        'covered': ov.get('covered', 0),
        'total': ov.get('total', len(folios))
    }

def check_benchmark(folios: list, benchmark_returns: dict) -> list:
    """
    Flag funds whose XIRR is below their specific benchmark 1-year return.
    """
    result = []
    for f in folios:
        if f.get('xirr') is None:
            continue
            
        cat = f.get('category', 'Equity')
        bm_name = benchmark_for(cat)
        bm_returns = benchmark_returns.get(bm_name, {})
        nifty_1y = bm_returns.get('1y', 0.12)
        
        fund_xirr_pct = f['xirr'] * 100
        nifty_pct = nifty_1y * 100
        
        if f['xirr'] < nifty_1y:
            result.append({
                'scheme':           f['scheme_name'],
                'fund_xirr':        round(fund_xirr_pct, 1),
                'nifty_return':     round(nifty_pct, 1),
                'underperformance': round(nifty_pct - fund_xirr_pct, 1),
                'benchmark_name':   bm_name
            })
    return result

def check_allocation(folios: list, user_age: int = 35) -> dict:
    total = sum(f.get('current_value', 0) for f in folios)
    if total == 0:
        return {}
    breakdown = {'large_cap': 0, 'mid_cap': 0, 'small_cap': 0, 'hybrid': 0, 'debt': 0}
    for f in folios:
        cat = f.get('category', '').lower()
        val = f.get('current_value', 0)
        pct = val / total
        if 'large cap' in cat or 'index' in cat:
            breakdown['large_cap'] += pct
        elif 'mid' in cat:
            breakdown['mid_cap'] += pct
        elif 'small' in cat:
            breakdown['small_cap'] += pct
        elif 'hybrid' in cat or 'balanced' in cat:
            breakdown['hybrid'] += pct
        elif 'debt' in cat or 'liquid' in cat or 'bond' in cat:
            breakdown['debt'] += pct
        else:
            breakdown['large_cap'] += pct  # default flexi/multi

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

def compute_health_score(overlap: dict, underperf: list, alloc: dict, conc: list) -> float:
    score = 100.0
    
    # Missing holdings data penalty
    if overlap.get('covered', 0) < overlap.get('total', 1):
        # We don't penalize score heavily if we just lack data, but maybe slight
        pass
        
    score -= min(overlap.get('toxicity_score', 0) * 0.5, 30)  # max 30 pts
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
    total_10 = 0
    for f in folios:
        ter_gap = f.get('ter_gap', 0.5)
        val = f.get('current_value', 0)
        # Assuming 0 monthly SIP here for baseline portfolio drag
        drag_10 = expense_drag(val, 0, ter_gap, 10)
        total_10 += drag_10
        
    # We can extrapolate for 20 and 30 linearly roughly for the return dictionary
    return {
        'total_drag_10yr_inr': round(total_10), 
        'total_drag_20yr_inr': round(total_10 * 2.8), # Approx compounding factor diff
        'total_drag_30yr_inr': round(total_10 * 5.6)
    }

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