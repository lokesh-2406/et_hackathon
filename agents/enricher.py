"""
Agent 2 — Enricher
Augments raw folio data with live NAV, XIRR, expense drag, and Nifty 50 benchmark.
"""
from utils.fund_lookup import find_scheme_code
from utils.mfapi import get_nav_history
from utils.calculations import compute_xirr, compute_expense_drag, total_invested
from utils.benchmark import get_benchmark_returns

DEFAULT_TER = 0.015
DIRECT_TER  = 0.005

def _enrich_folio(folio: dict) -> dict:
    name = folio.get('scheme_name', '')
    code = find_scheme_code(name)
    if not code:
        folio.update({'current_nav': folio.get('avg_nav', 0), 'current_value': round(folio.get('total_units', 0) * folio.get('avg_nav', 0), 2), 'xirr': None, 'total_invested': total_invested(folio.get('transactions', [])), 'expense_drag': {}, 'nav_fetched': False})
        return folio

    history = get_nav_history(code)
    current_nav = float(history[0]['nav']) if history else folio.get('avg_nav', 0)
    current_value = folio.get('total_units', 0) * current_nav
    
    folio.update({
        'scheme_code': code, 'current_nav': round(current_nav, 4), 'current_value': round(current_value, 2),
        'total_invested': round(total_invested(folio.get('transactions', [])), 2),
        'xirr': compute_xirr(folio.get('transactions', []), current_value),
        'expense_drag': compute_expense_drag(DEFAULT_TER, current_value), 'nav_fetched': True
    })
    return folio

def run_enricher(state: dict) -> dict:
    folios = state.get('folios', [])
    enriched = [_enrich_folio(f.copy()) for f in folios]
    nav_history_map = {f['scheme_code']: get_nav_history(f['scheme_code']) for f in enriched if f.get('scheme_code')}
    return {'folios': enriched, 'nav_history': nav_history_map, 'benchmark_returns': get_benchmark_returns()}