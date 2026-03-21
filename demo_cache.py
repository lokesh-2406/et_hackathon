"""
demo_cache.py — Golden demo cache builder
Run this script BEFORE the live demo to pre-compute and save the full pipeline
result for the golden synthetic portfolio. If anything fails during the demo,
load this cache instantly to continue without interruption.

Usage:
    # Build and save the cache (run once before demo):
    python demo_cache.py --pdf data/samples/golden.pdf

    # Verify the cache loaded correctly:
    python demo_cache.py --verify
"""
import argparse
import json
import os
import sys
from datetime import date


CACHE_PATH = 'data/golden_cache.json'

# Ideal golden portfolio — 8 funds designed to trigger maximum diagnostic signal
# See Sprint 12 of the build guide for the full rationale behind each fund.
GOLDEN_PORTFOLIO_NOTES = """
Golden Portfolio Composition (for reference when creating synthetic PDF):
  1. HDFC Top 100 Fund (Direct)       Rs 3,20,000  — overlap with Mirae
  2. Mirae Asset Large Cap Fund        Rs 2,80,000  — overlap with HDFC Top 100
  3. Axis Midcap Fund                  Rs 1,50,000  — XIRR below Nifty 50
  4. Parag Parikh Flexi Cap            Rs 4,50,000  — concentration risk (>30%)
  5. SBI Small Cap Fund                Rs   80,000  — small-cap overweight
  6. ICICI Pru Bluechip Fund           Rs 1,20,000  — third large-cap (extreme overlap)
  7. Franklin India Prima Fund         Rs   40,000  — tiny holding (rebalancing target)
  8. Kotak Debt Hybrid Fund            Rs   60,000  — adds hybrid / allocation analysis

Investor profile: Age 32, SIP Rs 15,000/month
"""


def build_and_save(pdf_path: str, age: int = 32, monthly_sip: float = 15000) -> dict:
    """Run the full pipeline on the golden PDF and save the result as JSON."""
    if not os.path.exists(pdf_path):
        print(f'ERROR: PDF not found at {pdf_path!r}')
        print(GOLDEN_PORTFOLIO_NOTES)
        sys.exit(1)

    from graph import portfolio_graph

    print(f'[demo_cache] Running full pipeline on {pdf_path}...')
    print(f'  Age: {age}  |  Monthly SIP: Rs {monthly_sip:,.0f}')

    initial_state = {
        'pdf_path':         pdf_path,
        'user_age':         age,
        'monthly_sip':      monthly_sip,
        'folios':           [],
        'parse_errors':     [],
        'nav_history':      {},
        'benchmark_returns':{},
        'fund_holdings':    {},
        'diagnostics':      {},
        'health_score':     0.0,
        'verdicts':         [],
        'rebalancing_plan': {},
        'glide_path':       [],
        'action_memo':      '',
        'watchlist':        [],
    }

    result = portfolio_graph.invoke(initial_state)

    os.makedirs('data', exist_ok=True)
    with open(CACHE_PATH, 'w', encoding='utf-8') as f:
        json.dump(result, f, default=str, indent=2)

    n_folios   = len(result.get('folios', []))
    score      = result.get('health_score', 0)
    n_verdicts = len(result.get('verdicts', []))
    n_actions  = len(result.get('rebalancing_plan', {}).get('actions', []))

    print(f'\n[demo_cache] Cache saved to {CACHE_PATH}')
    print(f'  Folios    : {n_folios}')
    print(f'  Score     : {score:.0f}/100')
    print(f'  Verdicts  : {n_verdicts}')
    print(f'  Actions   : {n_actions}')
    print('\nDemo tip: Press Ctrl+C during the live demo and run:')
    print('  python demo_cache.py --inject-to-session')
    return result


def verify_cache() -> None:
    """Load and print a summary of the cached result to confirm it's valid."""
    if not os.path.exists(CACHE_PATH):
        print(f'ERROR: No cache found at {CACHE_PATH}')
        print('Run:  python demo_cache.py --pdf data/samples/golden.pdf')
        sys.exit(1)

    with open(CACHE_PATH) as f:
        result = json.load(f)

    folios   = result.get('folios', [])
    score    = result.get('health_score', 0)
    verdicts = result.get('verdicts', [])
    plan     = result.get('rebalancing_plan', {})

    print(f'\n[demo_cache] Cache verification — {CACHE_PATH}')
    print(f'  Folios     : {len(folios)}')
    print(f'  Health     : {score:.0f}/100')
    print(f'  Verdicts   : {len(verdicts)}')
    print(f'  Actions    : {len(plan.get("actions", []))}')
    print(f'  Memo chars : {len(result.get("action_memo", ""))}')
    print(f'  Watchlist  : {len(result.get("watchlist", []))} trigger(s)')

    if verdicts:
        print('\n  Fund verdicts in cache:')
        for v in verdicts:
            print(f'    [{v.get("verdict","?")}] {v["fund"][:50]}  conviction {v.get("conviction","?")}')

    print('\n  Cache is valid and ready for demo.')


def main():
    parser = argparse.ArgumentParser(description='Portfolio Surgeon — Demo Cache Builder')
    parser.add_argument('--pdf',    help='Path to golden demo PDF')
    parser.add_argument('--age',    type=int,   default=32,    help='Investor age')
    parser.add_argument('--sip',    type=float, default=15000, help='Monthly SIP in Rs')
    parser.add_argument('--verify', action='store_true',       help='Verify existing cache')
    args = parser.parse_args()

    if args.verify:
        verify_cache()
    elif args.pdf:
        build_and_save(args.pdf, args.age, args.sip)
    else:
        parser.print_help()
        print(GOLDEN_PORTFOLIO_NOTES)


if __name__ == '__main__':
    main()