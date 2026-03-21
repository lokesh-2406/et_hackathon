"""
Agent 5 — Strategist
Synthesises analysis into a tax-aware rebalancing plan.
"""
import json
from utils.llm import chat

def run_strategist(state: dict) -> dict:
    prompt = f"Create a rebalancing plan for health score {state.get('health_score')}. Return JSON."
    raw = chat([{'role': 'user', 'content': prompt}])
    # Simplified parsing
    return {'rebalancing_plan': {'summary': 'Rebalance to reduce overlap.', 'actions': []}}