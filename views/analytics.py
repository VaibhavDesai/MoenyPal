"""Analytics view - Revamped with filters, KPIs, and better charts."""
import datetime as dt
import streamlit as st
import plotly.graph_objects as go
from models.analytics import monthly_totals, monthly_category_totals, get_kpi_metrics
from models.tag_analytics import tag_spending_over_time, top_tags_by_spending
from models.tags import list_all_tags
from utils.constants import CATEGORIES
from utils.helpers import category_label, format_ym


def render_analytics():
    """Render analytics tab with filters and KPIs."""
    st.markdown("""
    <div style="
        background: linear-gradient(135deg, #43e97b 0%, #38f9d7 100%);
        padding: 20px;
        border-radius: 16px;
        margin-bottom: 20px;
        box-shadow: 0 8px 24px rgba(67,233,123,0.25);
    ">
        <h1 style="
            color: white;
            margin: 0;
            font-size: 28px;
            font-weight: 600;
            text-shadow: 0 2px 4px rgba(0,0,0,0.1);
        ">📊 Analytics</h1>
        <p style="
            color: rgba(255,255,255,0.9);
            margin: 4px 0 0 0;
            font-size: 14px;
        ">Insights into your spending patterns</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Filters Section
    with st.expander("🔍 Filters", expanded=False):
        f1, f2 = st.columns([1, 1])
        with f1:
            date_range = st.date_input(
                "Date Range",
                value=(dt.date.today().replace(day=1) - dt.timedelta(days=180), dt.date.today()),
                key="analytics_date_range"
            )
        with f2:
            search_query = st.text_input(
                "Search",
                placeholder="Filter by item or category",
                key="analytics_search"
            )
    
    # Parse date range
    start_date = None
    end_date = None
    if isinstance(date_range, tuple) and len(date_range) == 2:
        start_date, end_date = date_range
    
    # Get KPI metrics
    kpis = get_kpi_metrics(start_date=start_date, end_date=end_date, search=search_query)
    
    # KPI Cards
    if kpis.get("transaction_count", 0) > 0:
        total_spent = (int(kpis.get("total_cents", 0)) / 100.0)
        avg_transaction = (int(kpis.get("avg_cents", 0)) / 100.0)
        transaction_count = int(kpis.get("transaction_count", 0))
        
        # Calculate daily average
        if start_date and end_date:
            days = (end_date - start_date).days + 1
            avg_daily = total_spent / days if days > 0 else 0
        else:
            avg_daily = 0
        
        kpi_cols = st.columns(4)
        with kpi_cols[0]:
            st.metric("Total Spent", f"${total_spent:,.0f}")
        with kpi_cols[1]:
            st.metric("Transactions", f"{transaction_count:,}")
        with kpi_cols[2]:
            st.metric("Avg/Transaction", f"${avg_transaction:,.0f}")
        with kpi_cols[3]:
            st.metric("Avg/Day", f"${avg_daily:,.0f}")
        
        st.markdown("---")
        
        # Monthly Trend Chart
        mom = monthly_totals(limit=12, start_date=start_date, end_date=end_date, search=search_query)
        
        if mom:
            with st.expander("📈 Monthly Trend", expanded=True):
                x = [format_ym(r["ym"]) for r in mom]
                y = [(int(r["total_cents"] or 0) / 100.0) for r in mom]
                
                fig_mom = go.Figure(
                    data=[
                        go.Scatter(
                            x=x,
                            y=y,
                            mode="lines+markers",
                            line=dict(color="#3b82f6", width=3),
                            marker=dict(size=8, symbol="circle"),
                            fill="tozeroy",
                            fillcolor="rgba(59,130,246,0.15)",
                            hovertemplate="<b>%{x}</b><br>$%{y:,.0f}<extra></extra>",
                        )
                    ]
                )
                fig_mom.update_layout(
                    template="plotly_dark",
                    margin=dict(l=20, r=20, t=20, b=20),
                    height=280,
                    paper_bgcolor="rgba(0,0,0,0)",
                    plot_bgcolor="rgba(0,0,0,0)",
                    xaxis=dict(
                        type="category",
                        tickangle=0,
                        tickfont=dict(size=11),
                        showgrid=False
                    ),
                    yaxis=dict(
                        title="",
                        gridcolor="rgba(255,255,255,0.08)",
                        tickprefix="$",
                        tickfont=dict(size=11)
                    ),
                )
                st.plotly_chart(fig_mom, use_container_width=True, config={"displayModeBar": False})
        
        # Category Breakdown
        mom_cat = monthly_category_totals(limit_months=6, start_date=start_date, end_date=end_date)
        
        if mom_cat:
            with st.expander("🎨 Category Breakdown", expanded=False):
                months = sorted({r["ym"] for r in mom_cat})
                months_fmt = [format_ym(m) for m in months]
                by_cat: dict[str, dict[str, float]] = {c: {m: 0.0 for m in months} for c in CATEGORIES}
                for r in mom_cat:
                    cat = r.get("category") or "misc"
                    if cat in by_cat:
                        by_cat[cat][r["ym"]] = float(int(r.get("total_cents") or 0) / 100.0)
                
                colors = {
                    "Fun": "#a855f7",
                    "groceris": "#22c55e",
                    "travel": "#06b6d4",
                    "home exp": "#f59e0b",
                    "misc": "#94a3b8",
                }
                
                fig_area = go.Figure()
                for cat in CATEGORIES:
                    fig_area.add_trace(
                        go.Scatter(
                            name=category_label(cat),
                            x=months_fmt,
                            y=[by_cat[cat][m] for m in months],
                            mode="lines",
                            line=dict(color=colors.get(cat, "#94a3b8"), width=2),
                            stackgroup="one",
                            hovertemplate=f"<b>{category_label(cat)}</b><br>%{{x}}: $%{{y:,.0f}}<extra></extra>",
                        )
                    )
                
                fig_area.update_layout(
                    template="plotly_dark",
                    margin=dict(l=20, r=20, t=20, b=20),
                    height=300,
                    showlegend=True,
                    legend=dict(
                        orientation="h",
                        yanchor="bottom",
                        y=1.02,
                        xanchor="left",
                        x=0,
                        font=dict(size=10)
                    ),
                    paper_bgcolor="rgba(0,0,0,0)",
                    plot_bgcolor="rgba(0,0,0,0)",
                    xaxis=dict(
                        type="category",
                        tickangle=0,
                        tickfont=dict(size=11),
                        showgrid=False
                    ),
                    yaxis=dict(
                        title="",
                        gridcolor="rgba(255,255,255,0.08)",
                        tickprefix="$",
                        tickfont=dict(size=11)
                    ),
                )
                st.plotly_chart(fig_area, use_container_width=True, config={"displayModeBar": False})
        
        # Tag Analytics
        all_tags = list_all_tags()
        if all_tags:
            with st.expander("🏷️ Tag Analytics", expanded=False):
                top_tags = top_tags_by_spending(limit=5)
                
                if top_tags:
                    st.caption("Top Tags")
                    top_cols = st.columns(min(len(top_tags), 3))
                    for idx, tag_data in enumerate(top_tags[:3]):
                        with top_cols[idx]:
                            tag_name = tag_data.get("tag_name", "")
                            total = (int(tag_data.get("total_cents", 0)) / 100.0)
                            count = int(tag_data.get("transaction_count", 0))
                            st.metric(f"#{tag_name}", f"${total:,.0f}", f"{count} txns")
                
                st.markdown("")
                selected_tag = st.selectbox(
                    "View tag trend",
                    options=all_tags,
                    key="tag_analytics_selector",
                )
                
                if selected_tag:
                    tag_data = tag_spending_over_time(selected_tag, limit_months=12)
                    
                    if tag_data:
                        x = [format_ym(r["ym"]) for r in tag_data]
                        y = [(int(r["total_cents"] or 0) / 100.0) for r in tag_data]
                        
                        fig_tag = go.Figure(
                            data=[
                                go.Scatter(
                                    x=x,
                                    y=y,
                                    mode="lines+markers",
                                    line=dict(color="#8b5cf6", width=3),
                                    marker=dict(size=7),
                                    fill="tozeroy",
                                    fillcolor="rgba(139,92,246,0.12)",
                                    hovertemplate="<b>%{x}</b><br>$%{y:,.0f}<extra></extra>",
                                )
                            ]
                        )
                        fig_tag.update_layout(
                            template="plotly_dark",
                            margin=dict(l=20, r=20, t=10, b=20),
                            height=240,
                            paper_bgcolor="rgba(0,0,0,0)",
                            plot_bgcolor="rgba(0,0,0,0)",
                            xaxis=dict(
                                type="category",
                                tickangle=0,
                                tickfont=dict(size=10),
                                showgrid=False
                            ),
                            yaxis=dict(
                                title="",
                                gridcolor="rgba(255,255,255,0.08)",
                                tickprefix="$",
                                tickfont=dict(size=10)
                            ),
                        )
                        st.plotly_chart(fig_tag, use_container_width=True, config={"displayModeBar": False})
    else:
        st.info("📝 No data available for the selected filters. Add some expenses to see analytics!")
