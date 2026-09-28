"""
Agent 4 — Debate Club
Uses LLM to simulate Bull vs Bear cases for top 5 funds.
"""
import time
from utils.llm import chat

<<<<<<< Updated upstream
=======
BULL_PROMPT = '''You are a bullish mutual fund analyst. Make the strongest possible case FOR holding or increasing allocation to this fund.

Fund: {scheme_name}
Current value: Rs {current_value:,.0f}
Portfolio weight: {weight:.1f}%
XIRR: {xirr_str}
Nifty 50 benchmark: {nifty:.1f}%
Diagnostics: {diagnostics_summary}

Write 3-4 punchy sentences. Reference the actual numbers above. Start with the strongest argument. Be specific, not generic.'''

BEAR_PROMPT = '''You are a critical mutual fund analyst. Present key flags, performance risks, and portfolio trade-offs against continuing full allocation to this fund.

Fund: {scheme_name}
Current value: Rs {current_value:,.0f}
Portfolio weight: {weight:.1f}%
XIRR: {xirr_str}
Nifty 50 benchmark: {nifty:.1f}%
Overlap with other funds: {overlap_info}
Diagnostics: {diagnostics_summary}

Write 3-4 punchy sentences. Reference the actual numbers above. Highlight the primary flags and trade-offs clearly.'''

JUDGE_PROMPT = '''You are a senior portfolio manager. You have heard arguments for and against this fund. Deliver a balanced verdict weighing flags and trade-offs.

Fund: {scheme_name}
Bull case: {bull_argument}
Bear case: {bear_argument}

Respond in this exact JSON format (no markdown, no explanation outside JSON):
{{
  "verdict": "HOLD" or "TRIM" or "EXIT" or "ADD",
  "conviction": <integer 1-10>,
  "reasoning": "<2-3 sentence balanced assessment of flags and trade-offs>",
  "action": "<specific actionable instruction, e.g. Reduce SIP by 50%>"
}}'''


def _debate_fund(folio: dict, total: float, diagnostics: dict, benchmark: dict) -> dict:
    name = folio['scheme_name']
    val = folio.get('current_value', 0)
    weight = val / total * 100 if total else 0
    raw_xirr = folio.get('xirr')
    xirr_str = f"{raw_xirr * 100:.1f}%" if raw_xirr is not None else "Insufficient history"
    nifty = benchmark.get('1y', 0.12) * 100

    pairs = diagnostics.get('overlap', {}).get('pairs', [])
    overlaps = [p for p in pairs if p['fund1'] == name or p['fund2'] == name]
    overlap_str = ', '.join(
        f"{p['fund1'] if p['fund2'] == name else p['fund2']} ({p['overlap_pct']}%)"
        for p in overlaps[:2]
    ) or 'None identified'

    diag_summary = (
        f"Health score: {diagnostics.get('health_score', 'N/A')}. "
        f"Underperformers: {len(diagnostics.get('underperformers', []))}. "
        f"Concentration issues: {len(diagnostics.get('concentration', []))}."
    )

    bull = chat([{'role': 'user', 'content': BULL_PROMPT.format(
        scheme_name=name, current_value=val, weight=weight,
        xirr_str=xirr_str, nifty=nifty, diagnostics_summary=diag_summary
    )}])

    bear = chat([{'role': 'user', 'content': BEAR_PROMPT.format(
        scheme_name=name, current_value=val, weight=weight,
        xirr_str=xirr_str, nifty=nifty, overlap_info=overlap_str,
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
            'xirr': round(raw_xirr * 100, 1) if raw_xirr is not None else None,
            **verdict}


>>>>>>> Stashed changes
def run_debate_club(state: dict) -> dict:
    folios = sorted(state.get('folios', []), key=lambda f: f.get('current_value', 0), reverse=True)[:5]
    verdicts = []
    for f in folios:
        # Simplified: 1 call for speed in this extract
        prompt = f"Debate this fund: {f['scheme_name']}. Provide Bull, Bear, and Verdict JSON."
        raw = chat([{'role': 'user', 'content': prompt}])
        verdicts.append({'fund': f['scheme_name'], 'verdict': 'HOLD', 'conviction': 7})
    return {'verdicts': verdicts}