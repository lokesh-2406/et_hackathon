# fund_lookup.py
from utils.mfapi import get_fund_list

def find_scheme_code(name: str) -> str | None:
    index = {f['schemeName'].lower(): str(f['schemeCode']) for f in get_fund_list()}
    return index.get(name.lower()) or next((c for n, c in index.items() if name.lower()[:20] in n), None)