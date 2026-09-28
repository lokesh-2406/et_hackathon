from pyxirr import xirr
from datetime import datetime, date

def parse_date(s: str) -> date:
    for fmt in ['%d-%b-%Y', '%d/%m/%Y', '%d-%m-%Y']:
        try: return datetime.strptime(s.strip(), fmt).date()
        except ValueError: continue
    raise ValueError(f"Date error: {s}")

def compute_xirr(txns: list, current_val: float) -> float | None:
<<<<<<< Updated upstream
    if not txns or current_val <= 0: return None
=======
    """
    Compute XIRR for a SIP portfolio.

    Args:
        txns:        List of transaction dicts with 'date' and 'amount' keys.
        current_val: Current market value of the holding (terminal inflow).

    Returns:
        XIRR as a decimal (e.g. 0.14 for 14%), or None if computation fails,
        transaction history is insufficient (<90 days), or result falls outside
        the sane range [-60%, +60%].
    """
    if not txns or current_val <= 0:
        return None
>>>>>>> Stashed changes
    try:
        parsed_dates = [parse_date(t['date']) for t in txns]
        dates = parsed_dates + [date.today()]
        # Check transaction date span: history < 90 days or fewer than 2 transactions is insufficient
        span_days = (date.today() - min(parsed_dates)).days
        if span_days < 90 or len(txns) < 2:
            print(f'[XIRR] History too short ({span_days} days, {len(txns)} txns). Flagging as insufficient history.')
            return None

        amts = [-abs(t['amount']) for t in txns] + [current_val]
<<<<<<< Updated upstream
        return float(xirr(dates, amts))
    except: return None

def compute_expense_drag(ter: float, corpus: float) -> dict:
    return {y: round(corpus * ((1.12)**y - (1.12-ter)**y), 2) for y in [10, 20, 30]}
=======
        result = float(xirr(dates, amts))

        # Data sufficiency flag: return None if outside sane range instead of clamping
        if not (_XIRR_MIN <= result <= _XIRR_MAX):
            print(f'[XIRR] Computed {result*100:.1f}% — outside sanity range [{_XIRR_MIN*100:.0f}%, {_XIRR_MAX*100:.0f}%]. Flagging as insufficient history.')
            return None

        return round(result, 4)
    except Exception as e:
        print(f'[XIRR] Computation failed: {e}')
        return None

def compute_expense_drag(ter: float, corpus: float) -> dict:
    """
    Compute wealth lost to regular plan TER vs direct plans over 10/20/30 years.

    Assumes 12% gross annual market return. Drag is the difference between direct plan
    compounding (12%) and regular plan compounding net of expense ratio (12% - ter).

    Returns dict with keys 10, 20, 30 (years) mapping to Rs drag.
    """
    if ter <= 0 or corpus <= 0:
        return {10: 0.0, 20: 0.0, 30: 0.0}
    return {
        y: round(corpus * ((1.12)**y - (1.12 - ter)**y), 2) for y in [10, 20, 30]
    }
>>>>>>> Stashed changes

def total_invested(txns: list) -> float:
    return sum(abs(t.get('amount', 0)) for t in txns)