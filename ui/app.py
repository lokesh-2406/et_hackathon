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
    render_expense_drag,
    render_overlap_pairs,
    render_xirr_chart,
    render_watchlist,
    render_holdings_table,
    verdict_badge,
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
</style>
''', unsafe_allow_html=True)

st.title('🔬 Portfolio Surgeon')
st.caption('6-agent AI system · AI Money Mentor · ET AI Hackathon 2026')

with st.sidebar:
    st.header('Your details')
    uploaded = st.file_uploader('Upload CAMS / KFintech PDF', type='pdf')
    age = st.slider('Your age', 22, 70, 32)
    monthly = st.number_input('Monthly SIP (Rs)', 0, 500000, 10000, 1000)
    run_btn = st.button('🚀 Analyse Portfolio', type='primary', use_container_width=True)
    demo_btn = st.button('🎬 Load Demo (cached)', use_container_width=True)

def run_pipeline(pdf_path: str, user_age: int, monthly_sip: float) -> dict:
    from graph import portfolio_graph
    agent_names = [
        ('parser', '📄 Parsing PDF statement'),
        ('enricher', '📊 Fetching live NAV & computing XIRR'),
        ('diagnostician', '🔍 Running 6 diagnostic checks'),
        ('debate_club', '🗣️ Running Bull / Bear / Judge debate'),
        ('strategist', '📋 Building tax-aware rebalancing plan'),
        ('executor', '📝 Generating action memo'),
        ('monitor', '🔔 Saving watchlist alerts'),
    ]
    progress_bar = st.progress(0)
    status_box = st.status('Portfolio Surgeon is running...', expanded=True)
    with status_box:
        for i, (_, label) in enumerate(agent_names):
            st.write(label)
            progress_bar.progress((i + 1) / len(agent_names))
        initial_state = {
            'pdf_path': pdf_path, 'user_age': user_age, 'monthly_sip': monthly_sip,
            'folios': [], 'parse_errors': [], 'nav_history': {}, 'benchmark_returns': {},
            'fund_holdings': {}, 'diagnostics': {}, 'health_score': 0.0, 'verdicts': [],
            'rebalancing_plan': {}, 'glide_path': [], 'action_memo': '', 'watchlist': [],
        }
        result = portfolio_graph.invoke(initial_state)
    status_box.update(label='✅ Analysis complete!', state='complete')
    return result

if run_btn and uploaded:
    os.makedirs('data', exist_ok=True)
    pdf_path = f'data/uploaded_{uploaded.name}'
    with open(pdf_path, 'wb') as f:
        f.write(uploaded.read())
    st.session_state['result'] = run_pipeline(pdf_path, age, monthly)
    st.session_state['source'] = 'live'
elif demo_btn:
    if os.path.exists('data/golden_cache.json'):
        with open('data/golden_cache.json') as f:
            st.session_state['result'] = json.load(f)
        st.session_state['source'] = 'demo'
        st.success('Loaded demo portfolio.')

if 'result' not in st.session_state:
    st.info('Upload a PDF or load demo.')
    st.stop()

r = st.session_state['result']
folios = r.get('folios', [])
diag = r.get('diagnostics', {})
verdicts = r.get('verdicts', [])
plan = r.get('rebalancing_plan', {})
score = r.get('health_score', 0.0)
memo = r.get('action_memo', '')
bench = r.get('benchmark_returns', {})
watchlist_data = r.get('watchlist', [])

total_val = sum(f.get('current_value', 0) for f in folios)
xirr_list = [f['xirr'] * 100 for f in folios if f.get('xirr') is not None]
avg_xirr = sum(xirr_list) / len(xirr_list) if xirr_list else 0.0

col1, col2, col3, col4, col5 = st.columns(5)
col1.metric('Portfolio Value', f'Rs {total_val:,.0f}')
col2.metric('Avg XIRR', f'{avg_xirr:.1f}%')
col3.metric('Health Score', f'{score:.0f}/100')
col4.metric('Funds', str(len(folios)))
col5.metric('Return', "Analysis Ready")

tab1, tab2, tab3, tab4, tab5 = st.tabs(['🔍 Diagnostics', '🗣️ Debate Club', '📋 Rebalancing Plan', '📝 Action Memo', '🔔 Watchlist'])

with tab1:
    d_col1, d_col2 = st.columns([1, 2])
    with d_col1:
        render_health_score(score)
        st.metric('Overlap Toxicity', f"{diag.get('overlap', {}).get('toxicity_score', 0)}/100")
    with d_col2:
        render_xirr_chart(folios, bench.get('1y', 0.12))
        alloc = diag.get('allocation', {})
        render_allocation_chart(alloc.get('breakdown', {}), alloc.get('recommended_equity_pct', 0), alloc.get('actual_equity_pct', 0))
    render_overlap_pairs(diag.get('overlap', {}).get('pairs', []))
    expense = diag.get('expense_drag', {})
    total_drag_20 = expense.get('total_drag_20yr_inr', 0)
    if total_drag_20 > 0:
        drag_10 = sum(f.get('expense_drag', {}).get(10, 0) for f in folios)
        drag_20 = total_drag_20
        drag_30 = sum(f.get('expense_drag', {}).get(30, 0) for f in folios)
        st.error(f'At current expense ratios, you will lose Rs {drag_20:,.0f} over 20 years vs direct plans.')
        fig = go.Figure(go.Bar(
            x=['10 years', '20 years', '30 years'],
            y=[drag_10, drag_20, drag_30],
            marker_color=['#FAC775', '#EF9F27', '#BA7517'],
            text=[f'Rs {v:,.0f}' for v in [drag_10, drag_20, drag_30]],
            textposition='outside'
        ))
        fig.update_layout(title='Wealth lost to expense ratios vs direct plans',
                        yaxis_title='Rs lost', height=300)
        st.plotly_chart(fig, use_container_width=True)

with tab2:
    for v in verdicts:
        with st.expander(f"{v.get('verdict', 'HOLD')} — {v['fund'][:55]}", expanded=False):
            st.write(f"Bull: {v.get('bull')}")
            st.write(f"Bear: {v.get('bear')}")
            st.write(f"Judge: {v.get('reasoning')}")

with tab3:
    st.write(plan.get('summary', ''))
    for action in plan.get('actions', []):
        st.info(f"[{action.get('action_type')}] {action.get('fund')}: {action.get('reason')}")

with tab4:
    st.code(memo)
    st.download_button('⬇️ Download Memo', memo, file_name='memo.txt')

with tab5:
    from agents.monitor import get_active_watchlist
    render_watchlist(get_active_watchlist() if os.path.exists('data/watchlist.db') else watchlist_data)