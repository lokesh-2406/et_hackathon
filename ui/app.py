"""
ui/app.py — Portfolio Surgeon Streamlit Application
Full 5-tab interface wired to the LangGraph pipeline.
"""
import sys
import os
import json
import streamlit as st
import plotly.graph_objects as go

# Make repo root importable
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ui.components import (
    render_health_score,
    render_allocation_chart,
    render_overlap_pairs,
    render_xirr_chart,
    render_watchlist,
)

st.set_page_config(
    page_title='Portfolio Surgeon',
    page_icon='🔬',
    layout='wide',
    initial_sidebar_state='expanded',
)

st.markdown('''
<style>
.stProgress > div > div > div { background-color: #1D9E75; }
div[data-testid="metric-container"] { background: #F1EFE8; border-radius: 8px; padding: 8px 12px; }
.verdict-hold  { background:#E8F5E9; border-radius:6px; padding:3px 10px; font-weight:600; color:#2E7D32; }
.verdict-trim  { background:#FFF8E1; border-radius:6px; padding:3px 10px; font-weight:600; color:#F9A825; }
.verdict-exit  { background:#FFEBEE; border-radius:6px; padding:3px 10px; font-weight:600; color:#C62828; }
.verdict-add   { background:#E3F2FD; border-radius:6px; padding:3px 10px; font-weight:600; color:#1565C0; }
</style>
''', unsafe_allow_html=True)

st.title('🔬 Portfolio Surgeon')
st.caption('7-agent AI system · AI Money Mentor · ET AI Hackathon 2026')

with st.sidebar:
    st.header('Your details')
    uploaded  = st.file_uploader('Upload CAMS / KFintech PDF', type='pdf')
    age       = st.slider('Your age', 22, 70, 32)
    monthly   = st.number_input('Monthly SIP (Rs)', 0, 500000, 10000, 1000)
    run_btn   = st.button('🚀 Analyse Portfolio', type='primary', use_container_width=True)
    demo_btn  = st.button('🎬 Load Demo (cached)', use_container_width=True)


def run_pipeline(pdf_path: str, user_age: int, monthly_sip: float) -> dict:
    from graph import portfolio_graph
    agent_steps = [
        '📄 Parsing PDF statement',
        '📊 Fetching live NAV & computing XIRR',
        '🔍 Running 6 diagnostic checks',
        '🗣️ Running Bull / Bear / Judge debate (15 LLM calls)',
        '📋 Building tax-aware rebalancing plan',
        '📝 Generating action memo',
        '🔔 Saving watchlist alerts',
    ]
    progress_bar = st.progress(0)
    status_box   = st.status('Portfolio Surgeon is running...', expanded=True)
    with status_box:
        for i, label in enumerate(agent_steps):
            st.write(label)
            progress_bar.progress((i + 1) / len(agent_steps))
        initial_state = {
            'pdf_path':    pdf_path,
            'user_age':    user_age,
            'monthly_sip': monthly_sip,
            'folios': [], 'parse_errors': [], 'nav_history': {},
            'benchmark_returns': {}, 'fund_holdings': {}, 'diagnostics': {},
            'health_score': 0.0, 'verdicts': [], 'rebalancing_plan': {},
            'glide_path': [], 'action_memo': '', 'watchlist': [],
        }
        result = portfolio_graph.invoke(initial_state)
    status_box.update(label='✅ Analysis complete!', state='complete')
    return result


# ── Session state management ────────────────────────────────────────────────

if run_btn and uploaded and not st.session_state.get('_running'):
    st.session_state['_running'] = True
    os.makedirs('data', exist_ok=True)
    pdf_path = f'data/uploaded_{uploaded.name}'
    with open(pdf_path, 'wb') as f:
        f.write(uploaded.read())
    st.session_state['result'] = run_pipeline(pdf_path, age, monthly)
    st.session_state['source'] = 'live'
    st.session_state['_running'] = False

elif demo_btn:
    if os.path.exists('data/golden_cache.json'):
        with open('data/golden_cache.json') as f:
            st.session_state['result'] = json.load(f)
        st.session_state['source'] = 'demo'
        st.success('Loaded demo portfolio (golden synthetic 8-fund portfolio, age 32).')
    else:
        st.error('Demo cache not found. Run: python demo_cache.py --pdf data/samples/golden_portfolio.pdf')

if 'result' not in st.session_state:
    st.info('Upload a CAMS/KFintech PDF or load the demo portfolio to get started.')
    st.stop()

r            = st.session_state['result']
folios       = r.get('folios', [])
diag         = r.get('diagnostics', {})
verdicts     = r.get('verdicts', [])
plan         = r.get('rebalancing_plan', {})
score        = r.get('health_score', 0.0)
memo         = r.get('action_memo', '')
bench        = r.get('benchmark_returns', {})
watchlist_data = r.get('watchlist', [])

total_val  = sum(f.get('current_value', 0) for f in folios)
xirr_list  = [f['xirr'] * 100 for f in folios if f.get('xirr') is not None]
avg_xirr   = sum(xirr_list) / len(xirr_list) if xirr_list else 0.0
nifty_1y   = bench.get('1y', 0.12) * 100

# ── Top-level metrics ────────────────────────────────────────────────────────

col1, col2, col3, col4, col5 = st.columns(5)
col1.metric('Portfolio Value',  f'Rs {total_val:,.0f}')
col2.metric('Avg XIRR',         f'{avg_xirr:.1f}%',
            delta=f'{avg_xirr - nifty_1y:+.1f}% vs Nifty')
col3.metric('Health Score',     f'{score:.0f}/100')
col4.metric('Funds',            str(len(folios)))
col5.metric('Nifty 50 (1yr)',   f'{nifty_1y:.1f}%')

# ── Tabs ─────────────────────────────────────────────────────────────────────

tab1, tab2, tab3, tab4, tab5 = st.tabs([
    '🔍 Diagnostics', '🗣️ Debate Club',
    '📋 Rebalancing Plan', '📝 Action Memo', '🔔 Watchlist',
])

# ── Tab 1: Diagnostics ───────────────────────────────────────────────────────
with tab1:
    d_col1, d_col2 = st.columns([1, 2])

    with d_col1:
        render_health_score(score)
        overlap_score = diag.get('overlap', {}).get('toxicity_score', 0)
        st.metric('Overlap Toxicity', f'{overlap_score}/100',
                  delta='⚠️ High' if overlap_score > 60 else '✓ Acceptable',
                  delta_color='inverse' if overlap_score > 60 else 'normal')
        n_under = len(diag.get('underperformers', []))
        st.metric('Underperformers', f'{n_under} fund(s)',
                  delta=f'below Nifty {nifty_1y:.1f}%')

    with d_col2:
        render_xirr_chart(folios, bench.get('1y', 0.12))
        alloc = diag.get('allocation', {})
        render_allocation_chart(
            alloc.get('breakdown', {}),
            alloc.get('recommended_equity_pct', 0),
            alloc.get('actual_equity_pct', 0),
        )

    render_overlap_pairs(diag.get('overlap', {}).get('pairs', []))

    # Expense drag — use correct keys from fixed diagnostician
    expense = diag.get('expense_drag', {})
    drag_10 = expense.get('total_drag_10yr_inr', 0)
    drag_20 = expense.get('total_drag_20yr_inr', 0)
    drag_30 = expense.get('total_drag_30yr_inr', 0)

    if drag_20 > 0:
        st.error(
            f'💸 At current expense ratios (regular plans), you will lose approximately '
            f'**Rs {drag_20:,.0f}** over 20 years vs equivalent direct plans.'
        )
        fig = go.Figure(go.Bar(
            x=['10 years', '20 years', '30 years'],
            y=[drag_10, drag_20, drag_30],
            marker_color=['#FAC775', '#EF9F27', '#BA7517'],
            text=[f'Rs {v:,.0f}' for v in [drag_10, drag_20, drag_30]],
            textposition='outside',
        ))
        fig.update_layout(
            title='Wealth lost to expense ratios vs direct plans',
            yaxis_title='Rs lost',
            height=300,
        )
        st.plotly_chart(fig, use_container_width=True)

# ── Tab 2: Debate Club ───────────────────────────────────────────────────────
with tab2:
    if not verdicts:
        st.info('No debate results yet. Run analysis first.')
    else:
        st.caption(f'Investment committee debate on top {len(verdicts)} funds by portfolio weight.')
        for v in verdicts:
            verdict_str = v.get('verdict', 'HOLD')
            conviction  = v.get('conviction', 0)
            xirr_val    = v.get('xirr', 0)
            css_class   = f'verdict-{verdict_str.lower()}'

            header = f"{v['fund'][:55]}  |  XIRR {xirr_val:.1f}%  |  Conviction {conviction}/10"
            with st.expander(header, expanded=False):
                vcol1, vcol2, vcol3 = st.columns(3)
                vcol1.markdown(f'<span class="{css_class}">{verdict_str}</span>',
                               unsafe_allow_html=True)
                vcol2.metric('Conviction', f'{conviction}/10')
                vcol3.metric('XIRR', f'{xirr_val:.1f}%',
                             delta=f'{xirr_val - bench.get("1y", 0.12)*100:+.1f}% vs Nifty')

                st.markdown('**🐂 Bull Case**')
                st.info(v.get('bull', 'N/A'))
                st.markdown('**🐻 Bear Case**')
                st.warning(v.get('bear', 'N/A'))
                st.markdown('**⚖️ Judge Verdict**')
                st.success(v.get('reasoning', 'N/A'))
                st.markdown(f'**Recommended action:** {v.get("action", "N/A")}')

# ── Tab 3: Rebalancing Plan ──────────────────────────────────────────────────
with tab3:
    summary = plan.get('summary', '')
    if summary:
        st.subheader('Executive Summary')
        st.write(summary)

    actions = plan.get('actions', [])
    if actions:
        st.subheader(f'Recommended Actions ({len(actions)})')
        for i, action in enumerate(actions, 1):
            action_type = action.get('action_type', 'REVIEW')
            fund        = action.get('fund', 'Unknown')
            reason      = action.get('reason', '')
            timing      = action.get('timing', 'Immediate')
            curr_sip    = action.get('current_sip')
            new_sip     = action.get('new_sip')

            color = {'EXIT': 'error', 'STOP_SIP': 'error',
                     'TRIM': 'warning', 'REDUCE_SIP': 'warning'}.get(action_type, 'info')
            getattr(st, color)(
                f'**{i}. [{action_type}]** {fund}\n\n'
                f'📅 Timing: {timing}  '
                + (f'  💰 SIP: Rs {curr_sip:,.0f} → Rs {new_sip:,.0f}' if curr_sip and new_sip else '') +
                f'\n\n{reason}'
            )

    target = plan.get('target_allocation', {})
    if target:
        st.subheader('Target Allocation')
        fig = go.Figure(go.Pie(
            labels=[k.replace('_', ' ').title() for k in target],
            values=list(target.values()),
            hole=0.4,
        ))
        fig.update_layout(height=300)
        st.plotly_chart(fig, use_container_width=True)

    new_funds = plan.get('new_funds_to_add', [])
    if new_funds:
        st.subheader('Suggested Additions')
        for nf in new_funds:
            st.write(f'• {nf}')

# ── Tab 4: Action Memo ───────────────────────────────────────────────────────
with tab4:
    if memo:
        st.download_button(
            '⬇️ Download Action Memo',
            memo,
            file_name='portfolio_surgeon_memo.txt',
            mime='text/plain',
        )
        st.code(memo, language=None)
    else:
        st.info('Action memo will appear here after analysis.')

# ── Tab 5: Watchlist ─────────────────────────────────────────────────────────
with tab5:
    from agents.monitor import get_active_watchlist
    live_wl = get_active_watchlist() if os.path.exists('data/watchlist.db') else watchlist_data
    render_watchlist(live_wl)