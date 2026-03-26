# utils/mfapi.py — full replacement with AMFI fallback

import requests
import re
from functools import lru_cache
from datetime import datetime

_SESSION = requests.Session()
_SESSION.headers.update({'User-Agent': 'PortfolioSurgeon/1.0'})

MFAPI_BASE = 'https://api.mfapi.in/mf'
AMFI_NAV_URL = 'https://www.amfiindia.com/spages/NAVAll.txt'


# ── AMFI fallback layer ────────────────────────────────────────────────────

@lru_cache(maxsize=1)
def _fetch_amfi_nav_text() -> str:
    """Fetch AMFI's daily NAV text file. Cached for the process lifetime."""
    r = _SESSION.get(AMFI_NAV_URL, timeout=15)
    r.raise_for_status()
    return r.text


def _parse_amfi_nav_text(text: str) -> dict:
    """
    Parse AMFI NAV text into {scheme_code_str: {'nav': float, 'name': str}}.
    Format: SchemeCode;ISIN1;ISIN2;SchemeName;NAV;Date
    """
    result = {}
    for line in text.splitlines():
        parts = line.split(';')
        if len(parts) < 6:
            continue
        code, _, _, name, nav_str, _ = parts[0], parts[1], parts[2], parts[3], parts[4], parts[5]
        try:
            result[code.strip()] = {'nav': float(nav_str.strip()), 'name': name.strip()}
        except ValueError:
            continue
    return result


@lru_cache(maxsize=1)
def _get_amfi_index() -> dict:
    return _parse_amfi_nav_text(_fetch_amfi_nav_text())


# ── mfapi.in layer ─────────────────────────────────────────────────────────

@lru_cache(maxsize=1)
def get_fund_list() -> list:
    """
    Returns [{schemeCode, schemeName}] for all funds.
    Falls back to building the list from AMFI if mfapi is down.
    """
    try:
        r = _SESSION.get(MFAPI_BASE, timeout=10)
        r.raise_for_status()
        return r.json()
    except Exception:
        index = _get_amfi_index()
        return [{'schemeCode': int(k), 'schemeName': v['name']} for k, v in index.items()]


@lru_cache(maxsize=500)
def get_nav_history(code: str) -> list:
    """
    Returns [{date: 'DD-Mon-YYYY', nav: '123.45'}] newest first.
    Falls back to single-entry list from AMFI if mfapi history is unavailable.
    """
    try:
        r = _SESSION.get(f'{MFAPI_BASE}/{code}', timeout=12)
        r.raise_for_status()
        data = r.json().get('data', [])
        if data:
            return data
    except Exception:
        pass

    # AMFI fallback — only current NAV, no history
    index = _get_amfi_index()
    entry = index.get(str(code))
    if entry:
        today = datetime.today().strftime('%d-%b-%Y')
        return [{'date': today, 'nav': str(entry['nav'])}]
    return []


def get_current_nav(code: str) -> float:
    history = get_nav_history(code)
    return float(history[0]['nav']) if history else 0.0


def search_fund(query: str) -> list:
    try:
        r = _SESSION.get(f'{MFAPI_BASE}/search?q={query.replace(" ", "+")}', timeout=10)
        r.raise_for_status()
        return r.json()
    except Exception:
        return []