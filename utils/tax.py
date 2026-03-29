from datetime import date
from utils.calculations import parse_date


def classify_gain(p_date_str: str, gain: float, is_debt: bool = False) -> dict:
    """
    Classify a capital gain as LTCG / STCG / DEBT_SLAB and provide timing advice.

    Args:
        p_date_str: Earliest purchase date string (DD-Mon-YYYY or DD/MM/YYYY)
        gain:       Unrealised gain in Rs (current_value - total_invested)
        is_debt:    True for pure debt funds (taxed at slab rate)

    Returns:
        dict with keys: type, tax_rate, days_held, advice
    """
    try:
        purchase_date = parse_date(p_date_str)
        days_held = (date.today() - purchase_date).days
    except Exception:
        return {
            'type': 'UNKNOWN',
            'tax_rate': 'N/A',
            'days_held': 0,
            'advice': 'Could not determine holding period — verify transaction dates.',
        }

    if is_debt:
        return {
            'type': 'DEBT_SLAB',
            'tax_rate': 'Slab rate',
            'days_held': days_held,
            'advice': 'Debt fund gains taxed at your income slab rate regardless of holding period.',
        }

    if days_held > 365:
        days_to_next_ltcg = 0
        advice = (
            'LTCG applicable (held >1 year). '
            'Tax: 12.5% on gains above ₹1.25 lakh exemption. '
            'Redeem now to get LTCG treatment.'
        )
        return {
            'type': 'LTCG',
            'tax_rate': '12.5%',
            'days_held': days_held,
            'advice': advice,
        }
    else:
        days_remaining = 365 - days_held
        advice = (
            f'STCG applicable (held {days_held} days). '
            f'Tax: 20% on gains. '
            f'Wait {days_remaining} more days for LTCG treatment (saves ~7.5% tax).'
        )
        return {
            'type': 'STCG',
            'tax_rate': '20%',
            'days_held': days_held,
            'advice': advice,
        }


def summarise_tax_for_portfolio(folios: list) -> list:
    results = []
    for f in folios[:5]:
        if f.get('transactions'):
            earliest = f['transactions'][0]['date']
            gain = f.get('current_value', 0) - sum(
                t.get('amount', 0) for t in f['transactions']
            )
            is_debt = any(
                k in f.get('scheme_name', '').lower()
                for k in ['debt', 'bond', 'liquid', 'gilt', 'overnight']
            )
            results.append(classify_gain(earliest, gain, is_debt))
    return results
