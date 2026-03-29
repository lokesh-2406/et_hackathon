"""
ui/components.py — Reusable Streamlit display components
"""
import streamlit as st
import plotly.graph_objects as go
import pandas as pd


def render_health_score(score: float) -> None:
    if score >= 75:
        bg, label = '#66BB6A', 'Good'
    elif score >= 50:
        bg, label = '#FFCA28', 'Needs Attention'
    else:
        bg, label = '#EF5350', 'Critical — Act Now'
    st.markdown(
        f'<div style="background:{bg};border-radius:12px;padding:20px;text-align:center;">'
        f'<div style="font-size:54px;font-weight:700;">{score:.0f}</div>'
        f'<div style="font-size:14px;">Portfolio Health Score / 100</div>'
        f'<div style="font-size:12px;color:#666;">{label}</div>'
        f'</div>',
        unsafe_allow_html=True,
    )


def render_allocation_chart(breakdown: dict, recommended_equity: float, actual_equity: float) -> None:
    if not breakdown:
        return
    fig = go.Figure(go.Bar(
        x=list(breakdown.values()),
        y=[k.replace('_', ' ').title() for k in breakdown.keys()],
        orientation='h',
        marker_color=['#4CAF50', '#2196F3', '#FF9800', '#9C27B0', '#607D8B'],
        text=[f'{v:.1f}%' for v in breakdown.values()],
        textposition='outside',
    ))
    fig.update_layout(
        title=f'Asset Allocation  (Actual equity {actual_equity:.0f}% vs Recommended {recommended_equity:.0f}%)',
        height=260,
        margin=dict(l=0, r=0, t=35, b=0),
        xaxis_title='% of portfolio',
    )
    st.plotly_chart(fig, use_container_width=True)


def render_xirr_chart(folios: list, benchmark_1y: float) -> None:
    data = [(f['scheme_name'][:28], f['xirr'] * 100)
            for f in folios if f.get('xirr') is not None]
    if not data:
        return
    names, xirrs = zip(*data)
    nifty_pct = benchmark_1y * 100
    colors = ['#EF5350' if x < nifty_pct else '#66BB6A' for x in xirrs]

    fig = go.Figure(go.Bar(
        x=names, y=xirrs,
        marker_color=colors,
        text=[f'{x:.1f}%' for x in xirrs],
        textposition='outside',
    ))
    fig.add_hline(
        y=nifty_pct, line_dash='dash', line_color='#1565C0',
        annotation_text=f'Nifty 50: {nifty_pct:.1f}%',
        annotation_position='top right',
    )
    fig.update_layout(
        title='XIRR per Fund vs Nifty 50 Benchmark',
        yaxis_title='XIRR %',
        height=300,
        margin=dict(l=0, r=0, t=35, b=0),
    )
    st.plotly_chart(fig, use_container_width=True)


def render_overlap_pairs(pairs: list) -> None:
    if not pairs:
        st.success('✓ No significant fund overlap detected.')
        return
    st.subheader(f'⚠️ Overlapping Fund Pairs ({len(pairs)} found)')
    for p in pairs:
        reason = p.get('reason', '')
        st.warning(
            f"**{p['fund1'][:40]}**  ↔  **{p['fund2'][:40]}**  "
            f"— estimated {p['overlap_pct']}% holdings overlap"
            + (f'\n_{reason}_' if reason else '')
        )


def render_watchlist(watchlist: list) -> None:
    if not watchlist:
        st.info('No active watchlist alerts.')
        return

    st.subheader(f'Active Alerts ({len(watchlist)})')
    for w in watchlist:
        trigger = w.get('trigger_type', '')
        fund    = w.get('fund_name', '')
        current = w.get('current_value', '')
        created = w.get('created_date', '')

        # Map trigger type to color
        if 'UNDERPERFORMANCE' in trigger or 'SELL' in trigger or 'EXIT' in trigger:
            fn = st.error
        elif 'CONCENTRATION' in trigger or 'OVERLAP' in trigger:
            fn = st.warning
        else:
            fn = st.info

        fn(
            f'**{trigger}**  ·  {fund}\n\n'
            f'{current}\n\n'
            f'_Detected: {created}_'
        )


def render_holdings_table(folios: list) -> None:
    """Render a sortable holdings table."""
    if not folios:
        return
    rows = []
    for f in folios:
        rows.append({
            'Fund':          f.get('scheme_name', ''),
            'Value (Rs)':    f.get('current_value', 0),
            'XIRR %':        round(f['xirr'] * 100, 1) if f.get('xirr') else None,
            'Units':         f.get('total_units', 0),
            'NAV':           f.get('current_nav', 0),
            'TER %':         round(f.get('real_ter', 0.015) * 100, 2),
        })
    df = pd.DataFrame(rows).sort_values('Value (Rs)', ascending=False)
    st.dataframe(df, use_container_width=True, hide_index=True)