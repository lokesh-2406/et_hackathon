from pyxirr import xirr
from datetime import datetime, date

# Reasonable bounds for equity mutual fund XIRR
_XIRR_MIN = -0.60   # -60%: worst realistic SIP outcome
_XIRR_MAX =  0.60   #  60%: best realistic SIP outcome (small cap bull run)

def parse_date(s: str) -> date:
    for fmt in ['%d-%b-%Y', '%d/%m/%Y', '%d-%m-%Y']:
        try: return datetime.strptime(s.strip(), fmt).date()
        except ValueError: continue
    raise ValueError(f"Date error: {s}")

def compute_xirr(txns: list, current_val: float) -> float | None:
    """
    Compute XIRR for a SIP portfolio.
 
    Args:
        txns:        List of transaction dicts with 'date' and 'amount' keys.
        current_val: Current market value of the holding (terminal inflow).
 
    Returns:
        XIRR as a decimal (e.g. 0.14 for 14%), or None if computation fails.
        Result is clamped to [_XIRR_MIN, _XIRR_MAX] to filter bad data.
    """
    if not txns or current_val <= 0: return None
    try:
        dates = [parse_date(t['date']) for t in txns] + [date.today()]
        amts = [-abs(t['amount']) for t in txns] + [current_val]
        result = float(xirr(dates, amts))
         # Sanity cap: flag extreme values rather than silently pass them
        if not (_XIRR_MIN <= result <= _XIRR_MAX):
            print(f'[XIRR] Warning: computed {result*100:.1f}% — outside sanity range, clamping.')
            result = max(_XIRR_MIN, min(_XIRR_MAX, result))
 
        return result
    except Exception as e:
        print(f'[XIRR] Computation failed: {e}')
        return None

def compute_expense_drag(ter: float, corpus: float) -> dict:
    """
    Compute wealth lost to TER vs direct plans over 10/20/30 years.
 
    Assumes 12% gross annual return. Drag = growth with direct (12%) minus
    growth with regular plan (12% - ter).
 
    Returns dict with keys 10, 20, 30 (years) mapping to Rs drag.
    """
    return {
        y: round(corpus * ((1.12)**y - (1.12-ter)**y), 2) for y in [10, 20, 30]
        }

def total_invested(txns: list) -> float:
    return sum(abs(t.get('amount', 0)) for t in txns)