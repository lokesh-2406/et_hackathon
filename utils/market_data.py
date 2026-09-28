"""utils/market_data.py - read-only lookups over data/market.db for the agents.

Copy this file into your repo's utils/ folder. Every function degrades gracefully
(returns None / {} ) when a table is missing, so the app never crashes in a demo.

    from utils.market_data import (get_ter, expense_drag, benchmark_for, benchmark_return,
                                   holdings_overlap, portfolio_overlap, look_through,
                                   peer_rank, better_alternatives)
"""
import difflib, re, sqlite3
from functools import lru_cache
from pathlib import Path
import pandas as pd

DB_PATH = Path(__file__).resolve().parent.parent / "data" / "market.db"

CATEGORY_BENCHMARK = [
    ("small cap", "NIFTY SMALLCAP 250"), ("mid cap", "NIFTY MIDCAP 150"),
    ("large & mid", "NIFTY LARGEMIDCAP 250"), ("large cap", "NIFTY 100"),
    ("flexi cap", "NIFTY 500"), ("multi cap", "NIFTY 500"), ("elss", "NIFTY 500"),
    ("focused", "NIFTY 500"), ("value", "NIFTY 500"), ("contra", "NIFTY 500"),
    ("index", "NIFTY 50"),
]


def _q(sql, params=()):
    if not DB_PATH.exists():
        return pd.DataFrame()
    try:
        with sqlite3.connect(DB_PATH) as con:
            return pd.read_sql_query(sql, con, params=params)
    except Exception:
        return pd.DataFrame()


def _norm(s):
    s = re.sub(r"\b(fund|plan|option|growth|direct|regular|scheme|the|of|-)\b", " ", str(s).lower())
    return re.sub(r"[^a-z0-9 ]+", " ", s).split()


@lru_cache(maxsize=1)
def _ter_table():
    df = _q("select Scheme_Name, SchemeCat_Desc, R_TER, D_TER from ter")
    if not df.empty:
        df["key"] = df.Scheme_Name.map(lambda x: " ".join(_norm(x)))
    return df


def _best_match(name, keys):
    target = " ".join(_norm(name))
    m = difflib.get_close_matches(target, keys, n=1, cutoff=0.6)
    return m[0] if m else None


def get_ter(scheme_name):
    """-> {'regular': 1.35, 'direct': 0.76, 'gap': 0.59, 'matched': 'HDFC Flexi Cap Fund'} or {}"""
    t = _ter_table()
    if t.empty:
        return {}
    k = _best_match(scheme_name, t.key.tolist())
    if not k:
        return {}
    r = t[t.key == k].iloc[0]
    return {"regular": float(r.R_TER), "direct": float(r.D_TER),
            "gap": float(r.R_TER - r.D_TER), "matched": r.Scheme_Name}


def expense_drag(current_value, monthly_sip, ter_gap_pct, years, gross_return=0.12):
    """Rupees lost to the Regular-vs-Direct TER gap over `years`.
    Compares end value at (gross - regular_ter) vs gross - direct_ter, i.e. the gap only."""
    def fv(rate):
        m = (1 + rate) ** (1 / 12) - 1
        n = years * 12
        sip_fv = monthly_sip * (((1 + m) ** n - 1) / m) * (1 + m) if m else monthly_sip * n
        return current_value * (1 + rate) ** years + sip_fv
    return fv(gross_return) - fv(gross_return - ter_gap_pct / 100)


def benchmark_for(category):
    c = str(category or "").lower()
    return next((b for k, b in CATEGORY_BENCHMARK if k in c), "NIFTY 50")


def benchmark_return(index_name, years=1):
    """Annualised TRI return over `years` ending at the latest date in the table."""
    df = _q("select date, tri from tri where index_name = ? order by date", (index_name,))
    if df.empty:
        return None
    df["date"] = pd.to_datetime(df.date)
    s = df.set_index("date").tri
    past = s[s.index <= s.index[-1] - pd.DateOffset(years=years)]
    if past.empty:
        return None
    return float((s.iloc[-1] / past.iloc[-1]) ** (1 / years) - 1)


@lru_cache(maxsize=1)
def _holdings():
    return _q("select fund_key, isin, stock, weight, sector from holdings")


def _fund_keys():
    h = _holdings()
    return sorted(h.fund_key.unique()) if not h.empty else []


def resolve_fund_key(scheme_name):
    keys = _fund_keys()
    if not keys:
        return None
    norm = {k: " ".join(_norm(k.replace("_", " "))) for k in keys}
    m = difflib.get_close_matches(" ".join(_norm(scheme_name)), list(norm.values()), n=1, cutoff=0.5)
    return next((k for k, v in norm.items() if v == m[0]), None) if m else None


def holdings_overlap(key_a, key_b):
    """Sum of min(weight) over shared stocks, in % of NAV (0-100). Standard overlap measure."""
    h = _holdings()
    if h.empty:
        return None
    a = h[h.fund_key == key_a].set_index("isin").weight
    b = h[h.fund_key == key_b].set_index("isin").weight
    common = a.index.intersection(b.index)
    shared = pd.concat([a[common], b[common]], axis=1).min(axis=1)
    return float(shared.sum())


def portfolio_overlap(funds):
    """funds: [(scheme_name, value_rs), ...] -> dict with 0-100 toxicity, worst pairs.
    Toxicity = value-weighted mean pairwise overlap."""
    keyed = [(resolve_fund_key(n), v, n) for n, v in funds]
    keyed = [x for x in keyed if x[0]]
    pairs, num, den = [], 0.0, 0.0
    for i in range(len(keyed)):
        for j in range(i + 1, len(keyed)):
            ov = holdings_overlap(keyed[i][0], keyed[j][0])
            if ov is None:
                continue
            w = keyed[i][1] * keyed[j][1]
            num += ov * w; den += w
            pairs.append((keyed[i][2], keyed[j][2], round(ov, 1)))
    return {"toxicity": round(num / den, 1) if den else None,
            "pairs": sorted(pairs, key=lambda p: -p[2]), "covered": len(keyed), "total": len(funds)}


def look_through(funds, top=10):
    """Effective stock exposure across the whole portfolio, in % of total portfolio."""
    h = _holdings()
    total = sum(v for _, v in funds) or 1
    parts = []
    for n, v in funds:
        k = resolve_fund_key(n)
        if k:
            f = h[h.fund_key == k].copy()
            f["exposure"] = f.weight / 100 * v / total * 100
            parts.append(f)
    if not parts:
        return pd.DataFrame()
    df = pd.concat(parts).groupby(["isin", "stock"], as_index=False).exposure.sum()
    return df.sort_values("exposure", ascending=False).head(top)


def peer_rank(scheme_name, plan="direct"):
    df = _q("select * from peer_stats where plan = ?", (plan,))
    if df.empty:
        return {}
    df["key"] = df.scheme_name.map(lambda x: " ".join(_norm(x)))
    k = _best_match(scheme_name, df.key.tolist())
    return df[df.key == k].iloc[0].to_dict() if k else {}


def better_alternatives(scheme_name, plan="direct", n=3):
    me = peer_rank(scheme_name, plan)
    if not me:
        return []
    df = _q("select scheme_name, cagr_3y, cagr_5y, sharpe_3y, maxdd_3y, pct_3y from peer_stats "
            "where category = ? and plan = ? and scheme_code != ? order by pct_3y desc limit ?",
            (me["category"], plan, int(me["scheme_code"]), n))
    return df.to_dict("records")
