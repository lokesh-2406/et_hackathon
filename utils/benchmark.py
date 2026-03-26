# utils/benchmark.py — add mftool fallback
from utils.mfapi import get_nav_history
from datetime import date, datetime, timedelta

NIFTY50_SCHEME = '120716'

def _benchmark_from_mftool() -> dict | None:
    try:
        from mftool import Mftool
        mf = Mftool()
        hist = mf.get_scheme_historical_nav(NIFTY50_SCHEME, as_Dataframe=True)
        if hist is None or hist.empty:
            return None
        hist = hist.sort_index(ascending=False)
        current = float(hist.iloc[0]['Net Asset Value'])
        def cagr_mf(days, years):
            target = date.today() - timedelta(days=days)
            past_rows = hist[hist.index <= str(target)]
            if past_rows.empty:
                return None
            past = float(past_rows.iloc[0]['Net Asset Value'])
            return (current / past) ** (1 / years) - 1
        return {
            '1y': cagr_mf(365, 1)     or 0.12,
            '3y': cagr_mf(365 * 3, 3) or 0.14,
            '5y': cagr_mf(365 * 5, 5) or 0.13,
        }
    except Exception:
        return None

def get_benchmark_returns() -> dict:
    try:
        hist = get_nav_history(NIFTY50_SCHEME)
        if not hist:
            raise ValueError('empty')
        current = float(hist[0]['nav'])

        def nav_on(days_ago: int) -> float | None:
            target = date.today() - timedelta(days=days_ago)
            for entry in hist:
                try:
                    d = datetime.strptime(entry['date'], '%d-%b-%Y').date()
                    if d <= target:
                        return float(entry['nav'])
                except Exception:
                    continue
            return None

        def cagr(past_nav, years):
            if not past_nav or past_nav <= 0:
                return None
            return (current / past_nav) ** (1 / years) - 1

        result = {
            '1y': cagr(nav_on(365), 1)     or 0.12,
            '3y': cagr(nav_on(365 * 3), 3) or 0.14,
            '5y': cagr(nav_on(365 * 5), 5) or 0.13,
        }
        # If all values are fallback defaults, mfapi history is probably truncated — try mftool
        if all(result[k] in (0.12, 0.14, 0.13) for k in result):
            mftool_result = _benchmark_from_mftool()
            if mftool_result:
                return mftool_result
        return result
    except Exception:
        return _benchmark_from_mftool() or {'1y': 0.12, '3y': 0.14, '5y': 0.13}