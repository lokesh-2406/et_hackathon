"""
agents/enricher.py — Enricher Agent

Re-written to use the unified local data pipeline (market.db).
"""

import logging

from utils.calculations import compute_xirr, total_invested
from utils.market_data import (
    get_ter,
    expense_drag,
    benchmark_for,
    benchmark_return,
    _norm,
    _q
)

DEFAULT_TER = 0.015

def _enrich_single_folio(folio: dict) -> dict:
    name = folio.get('scheme_name', '')
    
    # Check for metadata in the local DB
    # Find matching scheme in nav_master
    norm_name = " ".join(_norm(name))
    query = """
    SELECT * FROM nav_master 
    WHERE REPLACE(REPLACE(LOWER(scheme_name), '-', ' '), '  ', ' ') LIKE '%' || ? || '%' 
    LIMIT 1
    """
    df = _q(query, (norm_name,))
    
    code = None
    category = "Equity"
    plan = "Regular"
    
    if not df.empty:
        code = df.iloc[0]["scheme_code"]
        category = df.iloc[0]["category"]
        plan = df.iloc[0]["plan"]
        
    folio['scheme_code'] = code
    folio['category'] = category
    folio['plan'] = plan
    
    # TER from DB
    ter_data = get_ter(name)
    if ter_data:
        ter_val = ter_data.get("direct" if plan.lower() == "direct" else "regular", 1.5)
        folio['real_ter'] = ter_val / 100.0  # Decimal
        folio['ter_gap'] = ter_data.get('gap', 0)
    else:
        folio['real_ter'] = DEFAULT_TER
        folio['ter_gap'] = 0.5  # default gap

    if not code:
        folio.update({
            'current_nav': folio.get('avg_nav', 0),
            'current_value': round(folio.get('total_units', 0) * folio.get('avg_nav', 0), 2),
            'xirr': None,
            'total_invested': total_invested(folio.get('transactions', [])),
            'expense_drag': 0,
            'nav_fetched': False,
        })
        return folio

    # Get current NAV from DB (nav_history)
    hist_df = _q("SELECT nav FROM nav_history WHERE scheme_code = ? ORDER BY date DESC LIMIT 1", (code,))
    current_nav = float(hist_df.iloc[0]['nav']) if not hist_df.empty else folio.get('avg_nav', 0)
    
    current_val = folio.get('total_units', 0) * current_nav

    folio.update({
        'current_nav': round(current_nav, 4),
        'current_value': round(current_val, 2),
        'total_invested': round(total_invested(folio.get('transactions', [])), 2),
        'xirr': compute_xirr(folio.get('transactions', []), current_val),
        'expense_drag': round(expense_drag(current_val, 0, folio['ter_gap'], 10), 2), # Default 10 yrs drag
        'nav_fetched': True,
    })
    return folio

def run_enricher(state: dict) -> dict:
    folios = state.get('folios', [])
    enriched = []

    for f in folios:
        temp = f.copy()
        enriched.append(_enrich_single_folio(temp))

    matched = sum(1 for f in enriched if f.get('nav_fetched'))
    logging.info(f'[Enricher] {matched}/{len(enriched)} folios got live NAV from DB.')
    
    # Build benchmark returns dynamically from DB
    benchmark_returns = {}
    
    categories = set(f.get('category', 'Equity') for f in enriched)
    for cat in categories:
        bm = benchmark_for(cat)
        # Store bm returns
        benchmark_returns[bm] = {
            '1y': benchmark_return(bm, 1) or 0.12,
            '3y': benchmark_return(bm, 3) or 0.14,
            '5y': benchmark_return(bm, 5) or 0.13
        }
        
    return {'folios': enriched, 'benchmark_returns': benchmark_returns}