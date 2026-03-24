"""
Agent 5 — Strategist
Synthesises analysis into a tax-aware rebalancing plan.
"""
# agents/strategist.py — full replacement
import json
import re
from utils.llm import chat
from utils.tax import classify_gain

STRATEGY_PROMPT = '''You are a SEBI-registered mutual fund advisor. Based on the portfolio analysis below, create a specific, actionable rebalancing plan.

Portfolio health score: {health_score}/100
Total portfolio value: Rs {total_value:,.0f}

Debate verdicts:
{verdicts_summary}

Diagnostic flags:
- Overlap toxicity: {overlap_score}/100
- Underperformers vs Nifty: {underperf_count} funds
- Allocation balanced: {is_balanced}
- Total expense drag (20yr): Rs {expense_drag:,.0f}

Tax situation per fund:
{tax_summary}

Respond in JSON only (no markdown):
{{
  "summary": "<2 sentence overview of recommended changes>",
  "actions": [
    {{"fund": "<name>", "action_type": "STOP_SIP/REDUCE_SIP/EXIT/SWITCH_TO_DIRECT/HOLD/ADD_SIP/TRIM",
      "current_sip": <amount or null>, "new_sip": <amount or null>,
      "reason": "<specific reason referencing numbers>",
      "timing": "Immediate / Wait X months for LTCG"}}
  ],
  "new_funds_to_add": ["<fund category>"],
  "target_allocation": {{"large_cap": <pct>, "mid_cap": <pct>, "small_cap": <pct>, "debt": <pct>}},
  "priority_order": ["<first action>", "<second action>"]
}}'''


def run_strategist(state: dict) -> dict:
    folios = state.get('folios', [])
    verdicts = state.get('verdicts', [])
    diag = state.get('diagnostics', {})
    score = state.get('health_score', 0)
    bench = state.get('benchmark_returns', {})
    total_value = sum(f.get('current_value', 0) for f in folios)

    verdicts_summary = '\n'.join(
        f"- {v['fund']}: {v.get('verdict','?')} (conviction {v.get('conviction','?')}/10) — {v.get('action','')[:80]}"
        for v in verdicts
    ) or 'No verdicts available'

    tax_lines = []
    for f in folios[:5]:
        if f.get('transactions'):
            earliest = f['transactions'][0]['date']
            gain = f.get('current_value', 0) - sum(t.get('amount', 0) for t in f['transactions'])
            tinfo = classify_gain(earliest, gain)
            tax_lines.append(f"- {f['scheme_name'][:40]}: {tinfo['type']}, {tinfo.get('advice', '')}")
    tax_summary = '\n'.join(tax_lines) or 'No tax data available'

    prompt = STRATEGY_PROMPT.format(
        health_score=score,
        total_value=total_value,
        verdicts_summary=verdicts_summary,
        overlap_score=diag.get('overlap', {}).get('toxicity_score', 0),
        underperf_count=len(diag.get('underperformers', [])),
        is_balanced=diag.get('allocation', {}).get('is_balanced', 'unknown'),
        expense_drag=diag.get('expense_drag', {}).get('total_drag_20yr_inr', 0),
        tax_summary=tax_summary,
    )

    raw = chat([{'role': 'user', 'content': prompt}], temperature=0.2, max_tokens=1500)
    try:
        plan = json.loads(raw)
    except json.JSONDecodeError:
        m = re.search(r'\{.*\}', raw, re.DOTALL)
        plan = json.loads(m.group()) if m else {'summary': raw[:300], 'actions': []}

    print(f'[Strategist] Plan with {len(plan.get("actions", []))} actions generated')
    return {'rebalancing_plan': plan}