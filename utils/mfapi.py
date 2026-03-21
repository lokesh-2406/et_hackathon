import requests
import time
from functools import lru_cache

BASE = 'https://api.mfapi.in/mf'
_SESSION = requests.Session()

def _get(url: str) -> dict:
    r = _SESSION.get(url, timeout=15)
    r.raise_for_status()
    return r.json()

@lru_cache(maxsize=1)
def get_fund_list():
    return _get(BASE)

@lru_cache(maxsize=500)
def get_nav_history(code: str):
    return _get(f'{BASE}/{code}').get('data', [])

def search_fund(query: str):
    return _get(f'{BASE}/search?q={query.replace(" ", "+")}')