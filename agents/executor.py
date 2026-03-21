"""
Agent 6 — Executor
Converts the rebalancing plan into a formatted, downloadable action memo
that an investor can hand to their mutual fund distributor or use on an MFD platform.
"""
import os
from datetime import date


def _verdict_emoji(verdict: str) -> str:
    return {'HOLD': '[HOLD]', 'ADD': '[ADD]', 'TRIM': '[TRIM]', 'EXIT': '[EXIT]'}.get(verdict, '[?]')


def _action_label(action_type: str) -> str:
    labels = {
        'STOP_SIP':       'Stop SIP',
        'REDUCE_SIP':     'Reduce SIP',
        'EXIT':           'Full Redemption',
        'SWITCH_TO_DIRECT': 'Switch to Direct Plan',
        'HOLD':           'No Change',
        'ADD_SIP':        'Increase / Start SIP',
        'TRIM':           'Partial Redemption',
    }
    return labels.get(action_type, action_type)


def generate_memo(state: dict) -> str:
    """
    Build the complete plain-text action memo from portfolio state.

    Args:
        state: Full LangGraph portfolio state after all agents have run.

    Returns:
        Formatted multi-line string suitable for download or printing.
    """
    plan     = state.get('rebalancing_plan', {})
    folios   = state.get('folios', [])
    score    = state.get('health_score', 0)
    verdicts = state.get('verdicts', [])
    diag     = state.get('diagnostics', {})
    bench    = state.get('benchmark_returns', {})

    total_val = sum(f.get('current_value', 0) for f in folios)
    today = date.today().strftime('%d %B %Y')
    n_funds = len(folios)

    alloc = diag.get('allocation', {})
    expense = diag.get('expense_drag', {})
    overlap = diag.get('overlap', {})

    lines = [
        '=' * 64,
        '        PORTFOLIO SURGEON — PERSONALISED ACTION MEMO',
        '=' * 64,
        f'  Generated : {today}',
        f'  Funds     : {n_funds} folios analysed',
        f'  Value     : Rs {total_val:,.0f}',
        f'  Score     : {score:.0f}/100  '
        + ('(Good)' if score >= 75 else '(Needs Attention)' if score >= 50 else '(Critical — Act Now)'),
        '=' * 64,
        '',
        'EXECUTIVE SUMMARY',
        '-' * 40,
        plan.get('summary', 'No summary generated.'),
        '',
        'KEY DIAGNOSTIC FLAGS',
        '-' * 40,
        f'  Overlap toxicity   : {overlap.get("toxicity_score", 0)}/100'
        + ('  [HIGH - action needed]' if overlap.get('toxicity_score', 0) > 50 else '  [Acceptable]'),
        f'  Underperformers    : {len(diag.get("underperformers", []))} fund(s) below Nifty 50',
        f'  Concentration risk : {len(diag.get("concentration", []))} fund(s) > 30% of portfolio',
        f'  Allocation status  : {"Balanced" if alloc.get("is_balanced") else "Imbalanced"}  '
        f'(actual equity {alloc.get("actual_equity_pct", 0):.0f}% vs recommended {alloc.get("recommended_equity_pct", 0):.0f}%)',
        f'  Expense drag (20yr): Rs {expense.get("total_drag_20yr_inr", 0):,.0f}  '
        f'[{expense.get("total_drag_30yr_inr", 0):,.0f} over 30 years]',
        '',
        'RECOMMENDED ACTIONS',
        '-' * 40,
    ]

    actions = plan.get('actions', [])
    if not actions:
        lines.append('  No specific actions generated — review diagnostics above.')
    else:
        for i, action in enumerate(actions, 1):
            label = _action_label(action.get('action_type', 'REVIEW'))
            fund  = action.get('fund', 'Unknown')[:55]
            reason = action.get('reason', '')
            timing = action.get('timing', 'Immediate')
            curr_sip = action.get('current_sip')
            new_sip  = action.get('new_sip')

            lines += [
                f'{i:2}. [{label}]  {fund}',
                f'    Timing : {timing}',
            ]
            if curr_sip is not None and new_sip is not None:
                lines.append(f'    SIP    : Rs {curr_sip:,.0f}/mo  →  Rs {new_sip:,.0f}/mo')
            lines += [
                f'    Reason : {reason[:120]}',
                '',
            ]

    # Priority order
    priority = plan.get('priority_order', [])
    if priority:
        lines += ['PRIORITY ORDER', '-' * 40]
        for i, p in enumerate(priority, 1):
            lines.append(f'  {i}. {p}')
        lines.append('')

    # New funds to add
    new_funds = plan.get('new_funds_to_add', [])
    if new_funds:
        lines += ['SUGGESTED ADDITIONS', '-' * 40]
        for nf in new_funds:
            lines.append(f'  • {nf}')
        lines.append('')

    # Target allocation
    target = plan.get('target_allocation', {})
    if target:
        lines += ['TARGET ALLOCATION', '-' * 40]
        for cat, pct in target.items():
            bar = '█' * (int(pct) // 5)
            lines.append(f'  {cat.replace("_", " ").title():<20}  {pct:5.1f}%  {bar}')
        lines.append('')

    # Nifty 50 benchmark context
    lines += [
        'BENCHMARK CONTEXT',
        '-' * 40,
        f'  Nifty 50 (1yr)  : {bench.get("1y", 0) * 100:.1f}%',
        f'  Nifty 50 (3yr)  : {bench.get("3y", 0) * 100:.1f}% CAGR',
        f'  Nifty 50 (5yr)  : {bench.get("5y", 0) * 100:.1f}% CAGR',
        '',
    ]

    # Debate verdicts summary
    if verdicts:
        lines += ['FUND VERDICTS SUMMARY', '-' * 40]
        for v in verdicts:
            icon = _verdict_emoji(v.get('verdict', '?'))
            lines.append(
                f'  {icon}  {v["fund"][:45]:<45}  '
                f'Conviction {v.get("conviction", "?")}/10  |  XIRR {v.get("xirr", 0):.1f}%'
            )
        lines.append('')

    lines += [
        '=' * 64,
        'DISCLAIMER',
        '-' * 40,
        'This report is AI-generated analysis for educational purposes only.',
        'It does not constitute investment advice. Past performance does not',
        'guarantee future results. Consult a SEBI-registered investment advisor',
        'before making any investment decisions.',
        '',
        'Generated by Portfolio Surgeon — AI Money Mentor | ET AI Hackathon 2026',
        '=' * 64,
    ]

    return '\n'.join(lines)


def run_executor(state: dict) -> dict:
    """
    LangGraph node function for the Executor Agent.

    Generates the action memo text and saves it to data/action_memo.txt.
    Returns partial state update: {'action_memo': '...'}
    """
    print('[Executor] Generating action memo...')
    memo = generate_memo(state)

    # Save to disk so Streamlit's download button can serve it
    os.makedirs('data', exist_ok=True)
    memo_path = 'data/action_memo.txt'
    try:
        with open(memo_path, 'w', encoding='utf-8') as f:
            f.write(memo)
        print(f'[Executor] Memo saved to {memo_path} ({len(memo)} chars)')
    except IOError as e:
        print(f'[Executor] WARNING: Could not save memo to disk: {e}')

    return {'action_memo': memo}