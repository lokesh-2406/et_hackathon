from utils.mfapi import get_nav_history
from datetime import date, timedelta, datetime

NIFTY50_SCHEME = '120716'

def get_benchmark_returns() -> dict:
    try:
        hist = get_nav_history(NIFTY50_SCHEME)
        #added fallback returns in case of API failure or missing data, to ensure the pipeline can proceed with reasonable assumptions
        if not hist:
            return {'1y': 0.12, '3y': 0.14, '5y': 0.13}
        curr = float(hist[0]['nav'])
        def nav_on(days_ago: int) -> float | None:
            target = date.today() - timedelta(days=days_ago)
            for entry in hist:  # hist is newest-first
                try:
                    d = datetime.strptime(entry['date'], '%d-%b-%Y').date()
                    if d <= target:   # ← find first entry AT or BEFORE target
                        return float(entry['nav'])
                except Exception:
                    continue
            return None
        
        def cagr(past_nav, years):
            if not past_nav or past_nav <= 0:
                return None
            return (curr / past_nav) ** (1 / years) - 1
        return {
            '1y': cagr(nav_on(365), 1)   or 0.12,
            '3y': cagr(nav_on(365 * 3), 3) or 0.14,
            '5y': cagr(nav_on(365 * 5), 5) or 0.13,
        } # Fallback defaults
    except: return {'1y': 0.12, '3y': 0.14, '5y': 0.13}