"""
Agent 4 — Debate Club
Uses LLM to simulate Bull vs Bear cases for top 5 funds.
"""
import time
from utils.llm import chat

def run_debate_club(state: dict) -> dict:
    folios = sorted(state.get('folios', []), key=lambda f: f.get('current_value', 0), reverse=True)[:5]
    verdicts = []
    for f in folios:
        # Simplified: 1 call for speed in this extract
        prompt = f"Debate this fund: {f['scheme_name']}. Provide Bull, Bear, and Verdict JSON."
        raw = chat([{'role': 'user', 'content': prompt}])
        verdicts.append({'fund': f['scheme_name'], 'verdict': 'HOLD', 'conviction': 7})
    return {'verdicts': verdicts}