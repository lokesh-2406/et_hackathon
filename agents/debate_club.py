"""
Agent 4 — Debate Club
Uses LLM to simulate Bull vs Bear cases for top 5 funds using Real Data.
"""
import json
import re
import time
from utils.llm import chat

BULL_PROMPT = '''You are a bullish mutual fund analyst. Make the strongest possible case FOR holding or increasing allocation to this fund.

Fund: {scheme_name}
Current value: Rs {current_value:,.0f}
Portfolio weight: {weight:.1f}%
XIRR: {xirr:.1f}%
Specific Benchmark ({benchmark_name}): {nifty:.1f}%
Peer Group Percentiles: 1Y={pct_1y:.0f}%, 3Y={pct_3y:.0f}% (Higher is better)
3Y Sharpe Ratio: {sharpe_3y:.2f}
Diagnostics: {diagnostics_summary}

Write 3-4 punchy sentences. Reference the actual numbers above. Start with the strongest argument. Be specific, not generic.'''

BEAR_PROMPT = '''You are a bearish mutual fund analyst. Make the strongest possible case AGAINST this fund — argue for trimming or exiting.

Fund: {scheme_name}
Current value: Rs {current_value:,.0f}
Portfolio weight: {weight:.1f}%
XIRR: {xirr:.1f}%
Specific Benchmark ({benchmark_name}): {nifty:.1f}%
Peer Group Percentiles: 1Y={pct_1y:.0f}%, 3Y={pct_3y:.0f}% (Higher is better)
Max Drawdown: {maxdd:.1f}%
Total Expense Gap: {ter_gap:.2f}% (Drag: Rs {drag:,.0f})
Overlap with other funds: {overlap_info}
Diagnostics: {diagnostics_summary}

Write 3-4 punchy sentences. Reference the actual numbers above. Start with the most damning argument. Be direct.'''

JUDGE_PROMPT = '''You are a senior portfolio manager. You have heard arguments for and against this fund. Deliver a clear, decisive verdict.

Fund: {scheme_name}
Bull case: {bull_argument}
Bear case: {bear_argument}

Respond in this exact JSON format (no markdown, no explanation outside JSON):
{{
  "verdict": "HOLD" or "TRIM" or "EXIT" or "ADD",
  "conviction": <integer 1-10>,
  "reasoning": "<2-3 sentence summary of why this verdict>",
  "action": "<specific actionable instruction, e.g. Reduce SIP by 50%>"
}}'''


def _debate_fund(folio: dict, total: float, diagnostics: dict, benchmark_returns: dict) -> dict:
    name = folio['scheme_name']
    val = folio.get('current_value', 0)
    weight = val / total * 100 if total else 0
    xirr = (folio.get('xirr') or 0) * 100
    
    # Check for underperformance flag to get specific benchmark, otherwise use first or 12%
    underperf_flags = [u for u in diagnostics.get('underperformers', []) if u['scheme'] == name]
    if underperf_flags:
        nifty = underperf_flags[0]['nifty_return']
        bm_name = underperf_flags[0]['benchmark_name']
    else:
        # Generic fallback
        bm_name = "Benchmark"
        nifty = 12.0

    pairs = diagnostics.get('overlap', {}).get('pairs', [])
    overlaps = [p for p in pairs if p['fund1'] == name or p['fund2'] == name]
    overlap_str = ', '.join(
        f"{p['fund1'] if p['fund2'] == name else p['fund2']} ({p['overlap_pct']}%)"
        for p in overlaps[:2]
    ) or 'None identified'

    diag_summary = (
        f"Health score: {diagnostics.get('health_score', 'N/A')}. "
        f"Concentration issues: {len(diagnostics.get('concentration', []))}."
    )

    bull = chat([{'role': 'user', 'content': BULL_PROMPT.format(
        scheme_name=name, current_value=val, weight=weight,
        xirr=xirr, benchmark_name=bm_name, nifty=nifty,
        pct_1y=folio.get('pct_1y', 50), pct_3y=folio.get('pct_3y', 50),
        sharpe_3y=folio.get('sharpe_3y', 0),
        diagnostics_summary=diag_summary
    )}])

    bear = chat([{'role': 'user', 'content': BEAR_PROMPT.format(
        scheme_name=name, current_value=val, weight=weight,
        xirr=xirr, benchmark_name=bm_name, nifty=nifty,
        pct_1y=folio.get('pct_1y', 50), pct_3y=folio.get('pct_3y', 50),
        maxdd=folio.get('maxdd_3y', 0)*100, ter_gap=folio.get('ter_gap', 0.5),
        drag=folio.get('expense_drag', 0),
        overlap_info=overlap_str,
        diagnostics_summary=diag_summary
    )}])

    judge_raw = chat([{'role': 'user', 'content': JUDGE_PROMPT.format(
        scheme_name=name, bull_argument=bull, bear_argument=bear
    )}], temperature=0.1)

    try:
        verdict = json.loads(judge_raw)
    except json.JSONDecodeError:
        m = re.search(r'\{.*\}', judge_raw, re.DOTALL)
        verdict = json.loads(m.group()) if m else {
            'verdict': 'HOLD', 'conviction': 5,
            'reasoning': judge_raw[:200], 'action': 'Review manually'
        }

    return {'fund': name, 'bull': bull, 'bear': bear,
            'xirr': round(xirr, 1), **verdict}


def run_debate_club(state: dict) -> dict:
    folios = state.get('folios', [])
    total = sum(f.get('current_value', 0) for f in folios)
    diag = state.get('diagnostics', {})
    bench = state.get('benchmark_returns', {})

    top5 = sorted(folios, key=lambda f: f.get('current_value', 0), reverse=True)[:5]
    verdicts = []
    for i, folio in enumerate(top5):
        print(f'[Debate Club] Debating {folio["scheme_name"][:40]}...')
        verdicts.append(_debate_fund(folio, total, diag, bench))
        if i < len(top5) - 1:
            time.sleep(0.5)  # avoid rate limit

    return {'verdicts': verdicts}