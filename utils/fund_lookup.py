# fund_lookup.py
from utils.mfapi import get_fund_list

# def find_scheme_code(name: str) -> str | None:
#     index = {f['schemeName'].lower(): str(f['schemeCode']) for f in get_fund_list()}
#     return index.get(name.lower()) or next((c for n, c in index.items() if name.lower()[:20] in n), None)


# better handling of common suffixes, word-order variations, and minor typos in scheme names
def find_scheme_code(name: str) -> str | None:
    index = {f['schemeName'].lower(): str(f['schemeCode']) for f in get_fund_list()}
    name_clean = name.lower().strip()

    if name_clean in index:
        return index[name_clean]

    prefix = name_clean[:30]
    for sname, code in index.items():
        if prefix in sname:
            return code

    # Word-overlap fallback — catches "HDFC Top 100 Direct" vs "HDFC Top 100 Fund Direct Plan"
    words = set(name_clean.split())
    best_score, best_code = 0, None
    for sname, code in index.items():
        score = len(words & set(sname.split())) / max(len(words), 1)
        if score > best_score:
            best_score, best_code = score, code
    return best_code if best_score > 0.5 else None