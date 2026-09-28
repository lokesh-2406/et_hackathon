"""
Agent 5 — Strategist
Synthesises analysis into a tax-aware rebalancing plan.
"""
import json
from utils.llm import chat
<<<<<<< Updated upstream
=======
from utils.tax import classify_gain

STRATEGY_PROMPT = '''You are a SEBI-registered mutual fund advisor. Based on the portfolio analysis below, create a specific, balanced rebalancing plan highlighting key flags and trade-offs.

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

Guidelines:
- Present recommendations in terms of flags and trade-offs rather than blunt exit commands.
- Timing rules: SIP reductions/stops have NO tax consequence, so their timing is always "Immediate". LTCG timing ("Wait X months for LTCG") applies strictly to redemptions/trims to avoid STCG on units held under 1 year.

Respond in JSON only (no markdown):
{{
  "summary": "<2 sentence overview of recommended changes highlighting flags and trade-offs>",
  "actions": [
    {{"fund": "<name>", "action_type": "STOP_SIP/REDUCE_SIP/EXIT/SWITCH_TO_DIRECT/HOLD/ADD_SIP/TRIM",
      "current_sip": <amount or null>, "new_sip": <amount or null>,
      "reason": "<specific reason referencing flags, trade-offs, and numbers>",
      "timing": "Immediate (always for SIP changes; or for redemptions if already LTCG) / Wait X months for LTCG (only for redemptions to avoid STCG)"}}
  ],
  "new_funds_to_add": ["<fund category>"],
  "target_allocation": {{"large_cap": <pct>, "mid_cap": <pct>, "small_cap": <pct>, "debt": <pct>}},
  "priority_order": ["<first action>", "<second action>"]
}}'''

>>>>>>> Stashed changes

def run_strategist(state: dict) -> dict:
    prompt = f"Create a rebalancing plan for health score {state.get('health_score')}. Return JSON."
    raw = chat([{'role': 'user', 'content': prompt}])
    # Simplified parsing
    return {'rebalancing_plan': {'summary': 'Rebalance to reduce overlap.', 'actions': []}}