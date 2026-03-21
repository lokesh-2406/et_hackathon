from pyxirr import xirr
from datetime import datetime, date

def parse_date(s: str) -> date:
    for fmt in ['%d-%b-%Y', '%d/%m/%Y', '%d-%m-%Y']:
        try: return datetime.strptime(s.strip(), fmt).date()
        except ValueError: continue
    raise ValueError(f"Date error: {s}")

def compute_xirr(txns: list, current_val: float) -> float | None:
    if not txns or current_val <= 0: return None
    try:
        dates = [parse_date(t['date']) for t in txns] + [date.today()]
        amts = [-abs(t['amount']) for t in txns] + [current_val]
        return float(xirr(dates, amts))
    except: return None

def compute_expense_drag(ter: float, corpus: float) -> dict:
    return {y: round(corpus * ((1.12)**y - (1.12-ter)**y), 2) for y in [10, 20, 30]}

def total_invested(txns: list) -> float:
    return sum(abs(t.get('amount', 0)) for t in txns)