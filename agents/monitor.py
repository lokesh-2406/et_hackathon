"""
Agent 7 — Monitor
Persists actionable alerts to a SQLite watchlist database.
Triggers are generated from three sources:
  1. Underperforming funds (XIRR < Nifty 50)
  2. High-conviction EXIT or TRIM verdicts from the Debate Club
  3. Portfolio-level flags (high overlap toxicity, allocation imbalance)

The watchlist survives across sessions so an investor can track alerts over time.
"""
import sqlite3
import os
from datetime import date

DB_PATH = 'data/watchlist.db'


def init_db(db_path: str = DB_PATH) -> None:
    """Create the watchlist table if it does not already exist."""
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.execute('''
        CREATE TABLE IF NOT EXISTS watchlist (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            fund_name     TEXT    NOT NULL,
            trigger_type  TEXT    NOT NULL,
            threshold     TEXT,
            current_value TEXT,
            created_date  TEXT    NOT NULL,
            status        TEXT    DEFAULT "ACTIVE",
            resolved_date TEXT    DEFAULT NULL
        )
    ''')
    conn.commit()
    conn.close()


def save_triggers(triggers: list[dict], db_path: str = DB_PATH) -> int:
    """
    Insert new triggers into the watchlist table.
    Skips duplicates — a trigger is considered duplicate if the same
    fund_name + trigger_type already has an ACTIVE record created today.

    Returns the number of new records inserted.
    """
    if not triggers:
        return 0

    conn = sqlite3.connect(db_path)
    inserted = 0
    today = date.today().isoformat()

    for t in triggers:
        existing = conn.execute(
            'SELECT id FROM watchlist WHERE fund_name=? AND trigger_type=? AND created_date=? AND status="ACTIVE"',
            (t['fund_name'], t['trigger_type'], today),
        ).fetchone()
        if not existing:
            conn.execute(
                '''INSERT INTO watchlist (fund_name, trigger_type, threshold, current_value, created_date)
                   VALUES (:fund_name, :trigger_type, :threshold, :current_value, :created_date)''',
                {**t, 'created_date': today},
            )
            inserted += 1

    conn.commit()
    conn.close()
    return inserted


def get_active_watchlist(db_path: str = DB_PATH) -> list[dict]:
    """Fetch all ACTIVE watchlist records ordered by created_date descending."""
    try:
        conn = sqlite3.connect(db_path)
        rows = conn.execute(
            '''SELECT id, fund_name, trigger_type, threshold, current_value, created_date
               FROM watchlist WHERE status="ACTIVE" ORDER BY created_date DESC''',
        ).fetchall()
        conn.close()
        return [
            {
                'id': r[0], 'fund_name': r[1], 'trigger_type': r[2],
                'threshold': r[3], 'current_value': r[4], 'created_date': r[5],
            }
            for r in rows
        ]
    except Exception:
        return []


def resolve_trigger(trigger_id: int, db_path: str = DB_PATH) -> None:
    """Mark a watchlist alert as resolved."""
    conn = sqlite3.connect(db_path)
    conn.execute(
        'UPDATE watchlist SET status="RESOLVED", resolved_date=? WHERE id=?',
        (date.today().isoformat(), trigger_id),
    )
    conn.commit()
    conn.close()


def _build_triggers(state: dict) -> list[dict]:
    """
    Derive watchlist triggers from the current portfolio state.

    Three categories of triggers:
      UNDERPERFORMANCE      — fund XIRR below Nifty 50
      HIGH_CONVICTION_SELL  — Debate Club EXIT/TRIM with conviction >= 7
      HIGH_OVERLAP          — portfolio overlap toxicity score > 60
      ALLOCATION_IMBALANCE  — equity/debt split deviates > 10% from recommendation
      CONCENTRATION_RISK    — single fund > 30% of portfolio
    """
    diag     = state.get('diagnostics', {})
    verdicts = state.get('verdicts', [])
    folios   = state.get('folios', [])
    bench    = state.get('benchmark_returns', {})
    today    = date.today().isoformat()

    triggers: list[dict] = []

    # Trigger 1 — Underperformers
    for u in diag.get('underperformers', []):
        triggers.append({
            'fund_name':     u['scheme'][:100],
            'trigger_type':  'UNDERPERFORMANCE',
            'threshold':     f'XIRR must exceed Nifty 50 ({u.get("nifty_return", "N/A")}%)',
            'current_value': f'Fund XIRR = {u.get("fund_xirr", "N/A")}%  ({u.get("underperformance", "N/A")}% below benchmark)',
        })

    # Trigger 2 — High-conviction Debate Club sells
    for v in verdicts:
        conviction = v.get('conviction', 0)
        verdict    = v.get('verdict', '')
        if verdict in ('EXIT', 'TRIM') and conviction >= 7:
            triggers.append({
                'fund_name':     v['fund'][:100],
                'trigger_type':  'HIGH_CONVICTION_SELL',
                'threshold':     f'Conviction {conviction}/10 — {verdict}',
                'current_value': v.get('action', '')[:150],
            })

    # Trigger 3 — High overlap toxicity
    toxicity = diag.get('overlap', {}).get('toxicity_score', 0)
    if toxicity > 60:
        pair_names = '; '.join(
            f'{p["fund1"][:25]} ↔ {p["fund2"][:25]} ({p["overlap_pct"]}%)'
            for p in diag.get('overlap', {}).get('pairs', [])[:3]
        )
        triggers.append({
            'fund_name':     'PORTFOLIO',
            'trigger_type':  'HIGH_OVERLAP',
            'threshold':     'Overlap toxicity > 60/100',
            'current_value': f'Score: {toxicity}.  Overlapping pairs: {pair_names}',
        })

    # Trigger 4 — Allocation imbalance
    alloc = diag.get('allocation', {})
    if alloc and not alloc.get('is_balanced', True):
        triggers.append({
            'fund_name':     'PORTFOLIO',
            'trigger_type':  f'ALLOCATION_IMBALANCE: {alloc.get("deviation_pct", 0):.1f}% deviation from recommended',
            'threshold':     f'Recommended equity: {alloc.get("recommended_equity_pct", 0):.0f}%',
            'current_value': f'Actual equity: {alloc.get("actual_equity_pct", 0):.0f}%  '
                             f'(deviation {alloc.get("deviation_pct", 0):.1f}%)',
        })

    # Trigger 5 — Concentration risk
    for c in diag.get('concentration', []):
        triggers.append({
            'fund_name':     c['scheme'][:100],
            'trigger_type':  'CONCENTRATION_RISK',
            'threshold':     'Single fund > 30% of portfolio',
            'current_value': f'{c["pct"]}% of portfolio (Rs {c["current_value"]:,.0f})',
        })

    return triggers


def run_monitor(state: dict) -> dict:
    """
    LangGraph node function for the Monitor Agent.

    Derives triggers from portfolio state, saves them to SQLite, and returns
    the full active watchlist for display in the UI.

    Returns partial state update: {'watchlist': [...]}
    """
    print('[Monitor] Building watchlist triggers...')
    init_db()

    triggers = _build_triggers(state)
    n_inserted = save_triggers(triggers)
    print(f'[Monitor] {len(triggers)} trigger(s) generated, {n_inserted} new record(s) saved to DB')

    # Return the full active watchlist (includes triggers from previous runs)
    watchlist = get_active_watchlist()
    return {'watchlist': watchlist}