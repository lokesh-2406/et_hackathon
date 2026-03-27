"""
agents/enricher.py — Enricher Agent

Naming problem summary (from EDA on the Kaggle CSVs):

  Category 1 — Suffix mismatch (most common)
    PDF:  "Mirae Asset Large Cap Fund - Regular Plan - Growth"
    CSV:  "Mirae Asset Large Cap Fund"
    Fix:  Strip trailing plan/variant suffixes before matching.

  Category 2 — Fund absent from mutual_fund_data.csv
    "HDFC Top 100 Fund" is in Scheme_NAV_Name column but not Scheme_Name.
    "Franklin India Prima Fund" merged into Flexi Cap in 2021 — fully absent.
    Fix:  Fall back to Scheme_NAV_Name column, then to mfapi API search.

  Category 3 — Complete rename, no word overlap possible
    "IDFC Sterling Value Fund"    → "Bandhan Value Fund"      (Sterling dropped)
    "L&T Emerging Businesses Fund"→ "HSBC Small Cap Fund"     (completely different)
    "ICICI Pru Bluechip Fund"     → "ICICI Pru Large Cap Fund" (Bluechip→Large Cap)
    Fix:  Hard alias table applied before any matching.
"""

import os
import re
import logging
import pandas as pd

from utils.fund_lookup import find_scheme_code
from utils.mfapi import get_nav_history
from utils.calculations import compute_xirr, compute_expense_drag, total_invested
from utils.benchmark import get_benchmark_returns

DEFAULT_TER = 0.015

_DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data', 'samples')

# ---------------------------------------------------------------------------
# Hard alias table — Category 3 rebrands where name changed completely
# Key:   normalized old name (post suffix-strip, lowercase)
# Value: normalized new name to look up in CSV instead
# ---------------------------------------------------------------------------
_ALIASES: dict[str, str] = {
    # ICICI Pru Bluechip → ICICI Pru Large Cap (SEBI reclassification 2018)
    'icici pru bluechip fund':              'icici pru large cap fund',
    'icici prudential bluechip fund':       'icici pru large cap fund',

    # IDFC → Bandhan (acquisition 2022). "Sterling Value" → "Value"
    'idfc sterling value fund':             'bandhan value fund',
    'idfc tax advantage fund':              'bandhan tax advantage fund',
    'idfc banking and psu debt fund':       'bandhan banking and psu debt fund',
    'idfc bond fund short term plan':       'bandhan bond fund short term plan',
    'idfc dynamic bond fund':              'bandhan dynamic bond fund',
    'idfc flexi cap fund':                  'bandhan flexi cap fund',
    'idfc focused equity fund':             'bandhan focused equity fund',
    'idfc large cap fund':                  'bandhan large cap fund',
    'idfc mid cap fund':                   'bandhan midcap fund',
    'idfc nifty 50 index fund':             'bandhan nifty 50 index fund',
    'idfc overnight fund':                  'bandhan overnight fund',
    'idfc regular savings fund':            'bandhan regular savings fund',
    'idfc small cap fund':                  'bandhan small cap fund',

    # L&T → HSBC (acquisition 2023). Fund names changed.
    "l&t emerging businesses fund":         'hsbc small cap fund',
    "l&t midcap fund":                      'hsbc midcap fund',
    "l&t large cap fund":                   'hsbc large cap fund',
    "l&t flexi cap fund":                   'hsbc flexi cap fund',
    "l&t hybrid equity fund":               'hsbc aggressive hybrid fund',
    "l&t conservative hybrid fund":         'hsbc conservative hybrid fund',
    "l&t balanced advantage fund":          'hsbc balanced advantage fund',
    "l&t credit risk fund":                 'hsbc credit risk fund',
    "l&t liquid fund":                      'hsbc liquid fund',
    "l&t short term bond fund":             'hsbc short duration fund',
    "l&t gilt fund":                        'hsbc gilt fund',
    "l&t banking and psu debt fund":        'hsbc banking and psu debt fund',

    # Reliance → Nippon (2019)
    'reliance large cap fund':              'nippon india large cap fund',
    'reliance small cap fund':              'nippon india small cap fund',
    'reliance mid cap fund':                'nippon india growth fund',
    'reliance liquid fund':                 'nippon india liquid fund',
    'reliance tax saver fund':              'nippon india tax saver fund',
    'reliance equity opportunities fund':   'nippon india multicap fund',

    # Principal → Sundaram (2021)
    'principal emerging bluechip fund':     'sundaram emerging small cap fund',
    'principal mid cap fund':               'sundaram mid cap fund',
    'principal large cap fund':             'sundaram large cap fund',

    # Franklin Prima (merged into Flexi Cap 2021) — point to its successor
    'franklin india prima fund':            'franklin india flexi cap fund',
    'franklin india prima plus fund':       'franklin india flexi cap fund',
}


# ---------------------------------------------------------------------------
# Normalization
# ---------------------------------------------------------------------------

_SUFFIX_RE = re.compile(
    r'\s*[-–]\s*('
    r'regular plan|direct plan|regular|direct|'
    r'growth|idcw|dividend|bonus|'
    r'dir growth|dir|'
    r'weekly idcw|monthly idcw|quarterly idcw|annual idcw|'
    r'reinvestment|payout'
    r')\s*$',
    re.IGNORECASE,
)
_PARENS_RE    = re.compile(r'\s*\(.*?\)\s*')
_SPACES_RE    = re.compile(r'\s+')


def _normalize(name: str) -> str:
    """Lowercase, strip parens, strip trailing plan suffixes, collapse spaces."""
    n = name.lower().strip()
    n = _PARENS_RE.sub(' ', n)
    prev = None
    while prev != n:
        prev = n
        n = _SUFFIX_RE.sub('', n).strip().rstrip('-–').strip()
    # AMC abbreviations
    n = n.replace('icici prudential', 'icici pru')
    n = n.replace('aditya birla sun life', 'aditya birla sl')
    return _SPACES_RE.sub(' ', n).strip()


def _resolve_alias(norm: str) -> str:
    """Return aliased name if this is a known renamed/rebranded fund, else norm."""
    return _ALIASES.get(norm, norm)


# ---------------------------------------------------------------------------
# CSV loading
# ---------------------------------------------------------------------------

def _load_csvs() -> tuple[pd.DataFrame, pd.DataFrame]:
    lookup_path = os.path.join(_DATA_DIR, 'mutual_fund_data.csv')
    comp_path   = os.path.join(_DATA_DIR, 'comprehensive_mutual_funds_data.csv')

    try:
        lookup = pd.read_csv(lookup_path, dtype={'Scheme_Code': str})
        lookup['norm']     = lookup['Scheme_Name'].apply(_normalize)
        # Secondary match column — Scheme_NAV_Name catches funds like "HDFC Top 100 Fund"
        lookup['nav_norm'] = lookup['Scheme_NAV_Name'].apply(_normalize)
        logging.info(f'[Enricher] Loaded {len(lookup)} rows from mutual_fund_data.csv')
    except FileNotFoundError:
        logging.warning(f'[Enricher] mutual_fund_data.csv not found at {lookup_path}')
        lookup = pd.DataFrame(columns=['norm', 'nav_norm', 'Scheme_Code',
                                       'Scheme_Name', 'Scheme_Category',
                                       'ISIN_Div_Payout/Growth'])

    try:
        comp = pd.read_csv(comp_path)
        comp['norm'] = comp['scheme_name'].apply(_normalize)
        logging.info(f'[Enricher] Loaded {len(comp)} rows from comprehensive_mutual_funds_data.csv')
    except FileNotFoundError:
        logging.warning(f'[Enricher] comprehensive_mutual_funds_data.csv not found at {comp_path}')
        comp = pd.DataFrame(columns=['norm', 'scheme_name', 'expense_ratio',
                                     'fund_manager', 'rating'])

    return lookup, comp


LOOKUP_DF, COMP_DF = _load_csvs()


# ---------------------------------------------------------------------------
# Matching
# ---------------------------------------------------------------------------

def _match_lookup(folio_name: str) -> pd.Series | None:
    """
    Match against mutual_fund_data.csv in 4 passes:
      1. Exact on Scheme_Name norm
      2. Exact on Scheme_NAV_Name norm  (catches HDFC Top 100, etc.)
      3. First-4-words of PDF norm found in CSV norm
      4. Jaccard word overlap > 0.45
    """
    if LOOKUP_DF.empty:
        return None

    raw_norm  = _normalize(folio_name)
    query     = _resolve_alias(raw_norm)   # apply alias if fund was renamed
    words4    = ' '.join(query.split()[:4])

    # Pass 1 — exact on Scheme_Name
    hit = LOOKUP_DF[LOOKUP_DF['norm'] == query]
    if not hit.empty:
        return hit.iloc[0]

    # Pass 2 — exact on Scheme_NAV_Name
    hit = LOOKUP_DF[LOOKUP_DF['nav_norm'].str.startswith(words4, na=False)]
    if not hit.empty:
        return hit.iloc[0]

    # Pass 3 — first-4-words of query in CSV norm
    hit = LOOKUP_DF[LOOKUP_DF['norm'].str.contains(re.escape(words4), na=False)]
    if not hit.empty:
        return hit.iloc[0]

    # Pass 4 — Jaccard overlap
    qwords = set(query.split())
    best_j, best_idx = 0.0, None
    for idx, row in LOOKUP_DF.iterrows():
        cwords = set(row['norm'].split())
        j = len(qwords & cwords) / max(len(qwords | cwords), 1)
        if j > best_j:
            best_j, best_idx = j, idx
    if best_j >= 0.45 and best_idx is not None:
        return LOOKUP_DF.loc[best_idx]

    return None


def _match_comp(folio_name: str) -> pd.Series | None:
    """Match against comprehensive_mutual_funds_data.csv."""
    if COMP_DF.empty:
        return None

    raw_norm = _normalize(folio_name)
    query    = _resolve_alias(raw_norm)
    words4   = ' '.join(query.split()[:4])

    hit = COMP_DF[COMP_DF['norm'] == query]
    if not hit.empty:
        return hit.iloc[0]

    hit = COMP_DF[COMP_DF['norm'].str.contains(re.escape(words4), na=False)]
    if not hit.empty:
        return hit.iloc[0]

    # Jaccard
    qwords = set(query.split())
    best_j, best_idx = 0.0, None
    for idx, row in COMP_DF.iterrows():
        cwords = set(row['norm'].split())
        j = len(qwords & cwords) / max(len(qwords | cwords), 1)
        if j > best_j:
            best_j, best_idx = j, idx
    if best_j >= 0.45 and best_idx is not None:
        return COMP_DF.loc[best_idx]

    return None


# ---------------------------------------------------------------------------
# Per-folio enrichment
# ---------------------------------------------------------------------------

def _enrich_single_folio(folio: dict) -> dict:
    name  = folio.get('scheme_name', '')
    code  = folio.get('scheme_code') or find_scheme_code(name)

    if not code:
        folio.update({
            'current_nav':    folio.get('avg_nav', 0),
            'current_value':  round(folio.get('total_units', 0) * folio.get('avg_nav', 0), 2),
            'xirr':           None,
            'total_invested': total_invested(folio.get('transactions', [])),
            'expense_drag':   {},
            'nav_fetched':    False,
        })
        return folio

    history     = get_nav_history(str(code))
    current_nav = float(history[0]['nav']) if history else folio.get('avg_nav', 0)
    current_val = folio.get('total_units', 0) * current_nav
    ter         = folio.get('real_ter', DEFAULT_TER)

    folio.update({
        'scheme_code':    code,
        'current_nav':    round(current_nav, 4),
        'current_value':  round(current_val, 2),
        'total_invested': round(total_invested(folio.get('transactions', [])), 2),
        'xirr':           compute_xirr(folio.get('transactions', []), current_val),
        'expense_drag':   compute_expense_drag(ter, current_val),
        'nav_fetched':    True,
    })
    return folio


# ---------------------------------------------------------------------------
# LangGraph node
# ---------------------------------------------------------------------------

def run_enricher(state: dict) -> dict:
    folios   = state.get('folios', [])
    enriched = []

    for f in folios:
        temp = f.copy()
        name = temp.get('scheme_name', '')

        # ── Step 1: Scheme_Code + ISIN + Category from lookup CSV ────────────
        lrow = _match_lookup(name)
        if lrow is not None:
            temp['scheme_code'] = str(lrow.get('Scheme_Code', '')).strip()
            temp['isin']        = str(lrow.get('ISIN_Div_Payout/Growth',
                                               temp.get('isin', ''))).strip()
            temp['category']    = str(lrow.get('Scheme_Category', 'Equity')).strip()
            logging.info(f"[Enricher] Lookup  '{name[:45]}' → {temp['scheme_code']}")
        else:
            logging.warning(f"[Enricher] No lookup match for '{name}' — will try API name search")

        # ── Step 2: TER + fund_manager + rating from comprehensive CSV ────────
        crow = _match_comp(name)
        if crow is not None:
            raw_ter = crow.get('expense_ratio', DEFAULT_TER * 100)
            temp['real_ter']     = float(raw_ter) / 100
            temp['fund_manager'] = str(crow.get('fund_manager', 'Unknown'))
            temp['rating']       = int(crow.get('rating', 0))
            temp['returns_1yr']  = float(crow.get('returns_1yr', 0))
            temp['returns_3yr']  = float(crow.get('returns_3yr', 0))
            logging.info(f"[Enricher] Comp    '{name[:45]}' → TER {temp['real_ter']:.3f}")
        else:
            temp['real_ter'] = DEFAULT_TER

        # ── Step 3: Live NAV + XIRR + expense drag ───────────────────────────
        enriched.append(_enrich_single_folio(temp))

    benchmark = get_benchmark_returns()
    matched   = sum(1 for f in enriched if f.get('nav_fetched'))
    logging.info(f'[Enricher] {matched}/{len(enriched)} folios got live NAV.')

    return {'folios': enriched, 'benchmark_returns': benchmark}