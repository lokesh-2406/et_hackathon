"""
ui/components.py — Reusable Streamlit display components
"""
import streamlit as st
import plotly.graph_objects as go
import pandas as pd

def render_health_score(score: float) -> None:
    bg = '#EAF3DE' if score >= 75 else '#FAEEDA' if score >= 50 else '#FCEBEB'
    st.markdown(f'<div style="background:{bg};border-radius:12px;padding:20px;text-align:center;">'
                f'<div style="font-size:54px;font-weight:700;">{score:.0f}</div>'
                f'<div>Portfolio Health Score / 100</div></div>', unsafe_allow_html=True)

def render_allocation_chart(breakdown: dict, recommended_equity: float, actual_equity: float) -> None:
    fig = go.Figure(go.Bar(x=list(breakdown.values()), y=list(breakdown.keys()), orientation='h'))
    fig.update_layout(title='Asset Allocation', height=280)
    st.plotly_chart(fig, use_container_width=True)

def render_xirr_chart(folios: list, benchmark_1y: float) -> None:
    names = [f['scheme_name'][:30] for f in folios if f.get('xirr') is not None]
    xirrs = [f['xirr'] * 100 for f in folios if f.get('xirr') is not None]
    fig = go.Figure(go.Bar(x=names, y=xirrs))
    fig.add_hline(y=benchmark_1y * 100, line_dash="dash", line_color="blue")
    st.plotly_chart(fig, use_container_width=True)

def render_overlap_pairs(pairs: list) -> None:
    for p in pairs:
        st.warning(f"{p['fund1']} ↔ {p['fund2']} ({p['overlap_pct']}% overlap)")

def render_watchlist(watchlist: list) -> None:
    for w in watchlist:
        st.info(f"{w['trigger_type']}: {w['fund_name']} | {w['current_value']}")

def render_holdings_table(folios: list) -> None:
    df = pd.DataFrame([{'Fund': f['scheme_name'], 'Value': f.get('current_value'), 'XIRR': f.get('xirr')} for f in folios])
    st.dataframe(df)

def verdict_badge(verdict: str) -> str:
    return f'<span style="padding:3px 10px;border-radius:6px;font-weight:600">{verdict}</span>'

def render_expense_drag(folios: list, d10: float, d20: float, d30: float) -> None:
    st.bar_chart({'10yr': d10, '20yr': d20, '30yr': d30})