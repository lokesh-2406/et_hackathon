# tax.py
from datetime import date
from utils.calculations import parse_date

def classify_gain(p_date_str: str, gain: float, is_debt: bool = False) -> dict:
    days = (date.today() - parse_date(p_date_str)).days
    if is_debt: return {'type': 'DEBT_SLAB', 'tax_rate': '30%'}
    return {'type': 'LTCG' if days > 365 else 'STCG', 'tax_rate': '12.5%' if days > 365 else '20%'}

def summarise_tax_for_portfolio(folios: list) -> list:
    return [classify_gain(f['transactions'][0]['date'], f['current_value'] - 1000) for f in folios[:3] if f.get('transactions')]

