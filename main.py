"""
main.py — CLI entry point
Run the full Portfolio Surgeon pipeline from the terminal without Streamlit.
Useful for debugging, caching golden output, and CI testing.

Usage:
    python main.py --pdf data/samples/test.pdf --age 32 --sip 15000
    python main.py --pdf data/samples/test.pdf --age 32 --sip 15000 --save-cache
"""
import argparse
import json
import sys
import os


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description='Portfolio Surgeon — AI Mutual Fund Analyser',
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument('--pdf',        required=True,  help='Path to CAMS/KFintech PDF statement')
    parser.add_argument('--age',        type=int,       default=32,    help='Investor age (default: 32)')
    parser.add_argument('--sip',        type=float,     default=10000, help='Monthly SIP in Rs (default: 10000)')
    parser.add_argument('--save-cache', action='store_true',           help='Save result to data/golden_cache.json')
    parser.add_argument('--from-cache', action='store_true',           help='Load and display cached result instead of running pipeline')
    return parser.parse_args()


def print_summary(result: dict) -> None:
    """Print a compact terminal summary of the pipeline result."""
    folios   = result.get('folios', [])
    score    = result.get('health_score', 0)
    verdicts = result.get('verdicts', [])
    plan     = result.get('rebalancing_plan', {})
    errors   = result.get('parse_errors', [])
    watchlist= result.get('watchlist', [])

    total_val = sum(f.get('current_value', 0) for f in folios)
    xirrs = [f['xirr'] * 100 for f in folios if f.get('xirr')]
    avg_xirr = sum(xirrs) / len(xirrs) if xirrs else 0

    print('\n' + '=' * 60)
    print('  PORTFOLIO SURGEON — RESULTS')
    print('=' * 60)
    print(f'  Folios analysed : {len(folios)}')
    print(f'  Portfolio value : Rs {total_val:,.0f}')
    print(f'  Average XIRR    : {avg_xirr:.1f}%')
    print(f'  Health score    : {score:.0f}/100')
    print(f'  Parse errors    : {errors or "None"}')

    if verdicts:
        print('\n  FUND VERDICTS')
        print('  ' + '-' * 50)
        for v in verdicts:
            print(f'  [{v.get("verdict","?")}] {v["fund"][:45]:<45}  conviction {v.get("conviction","?")}')

    if plan.get('actions'):
        print('\n  REBALANCING ACTIONS')
        print('  ' + '-' * 50)
        for a in plan['actions']:
            print(f'  {a.get("action_type",""):<20}  {a.get("fund","")[:40]}')

    if watchlist:
        print(f'\n  WATCHLIST ALERTS : {len(watchlist)} active trigger(s)')

    print('\n  Action memo saved to: data/action_memo.txt')
    print('=' * 60)


def main() -> None:
    args = parse_args()

    # Load from cache if requested
    if args.from_cache:
        cache_path = 'data/golden_cache.json'
        if not os.path.exists(cache_path):
            print(f'ERROR: Cache file not found at {cache_path}')
            sys.exit(1)
        with open(cache_path) as f:
            result = json.load(f)
        print('[main] Loaded result from cache.')
        print_summary(result)
        return

    # Validate PDF path
    if not os.path.exists(args.pdf):
        print(f'ERROR: PDF not found at {args.pdf!r}')
        sys.exit(1)

    # Import here so startup errors in agents surface clearly
    from graph import portfolio_graph

    print(f'\n[main] Starting Portfolio Surgeon pipeline...')
    print(f'  PDF  : {args.pdf}')
    print(f'  Age  : {args.age}')
    print(f'  SIP  : Rs {args.sip:,.0f}/month\n')

    initial_state = {
        'pdf_path':    args.pdf,
        'user_age':    args.age,
        'monthly_sip': args.sip,
        # Pre-populate optional keys to avoid TypedDict KeyError in stub agents
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
    print_summary(result)

    # Save cache if requested
    if args.save_cache:
        os.makedirs('data', exist_ok=True)
        cache_path = 'data/golden_cache.json'
        with open(cache_path, 'w') as f:
            json.dump(result, f, default=str, indent=2)
        print(f'\n[main] Result cached to {cache_path}')


if __name__ == '__main__':
    main()