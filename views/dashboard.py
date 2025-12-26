"""Dashboard view."""
import datetime as dt
import calendar
import streamlit as st
import plotly.graph_objects as go
from models.expense import spent_by_category_for_month, spent_total_for_month
from models.settings import get_settings
from utils.constants import CATEGORIES
from utils.helpers import category_label


def render_dashboard():
    """Render dashboard tab."""
    today = dt.date.today()
    days_in_month = calendar.monthrange(today.year, today.month)[1]
    days_remaining = days_in_month - today.day

    st.markdown(f"""
    <div style="
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 20px;
        border-radius: 16px;
        margin-bottom: 20px;
        box-shadow: 0 8px 24px rgba(102,126,234,0.25);
    ">
        <h1 style="
            color: white;
            margin: 0;
            font-size: 28px;
            font-weight: 600;
            text-shadow: 0 2px 4px rgba(0,0,0,0.1);
        ">{days_remaining} days remaining</h1>
        <p style="
            color: rgba(255,255,255,0.9);
            margin: 4px 0 0 0;
            font-size: 14px;
        ">{today.strftime('%B %Y')}</p>
    </div>
    """, unsafe_allow_html=True)

    settings = get_settings()
    income_1 = (settings.get("income_1_cents", 0) or 0) / 100.0
    income_2 = (settings.get("income_2_cents", 0) or 0) / 100.0
    saving_goal_pct = float(settings.get("saving_goal_pct", 0.0) or 0.0)

    total_income = income_1 + income_2
    spending_budget = total_income * (1.0 - (saving_goal_pct / 100.0))

    spent = spent_total_for_month(today) / 100.0
    remaining = max(spending_budget - spent, 0.0)

    budget = max(spending_budget, 0.0)
    spent_clamped = min(max(spent, 0.0), budget) if budget > 0 else 0.0
    remaining_clamped = max(budget - spent_clamped, 0.0)

    fig = go.Figure(
        data=[
            go.Pie(
                values=[spent_clamped, remaining_clamped],
                hole=0.75,
                sort=False,
                direction="clockwise",
                rotation=90,
                marker={
                    "colors": ["#f87171", "#34d399"],
                    "line": {"color": "rgba(255,255,255,0.8)", "width": 3}
                },
                textinfo="none",
                hovertemplate="<b>%{label}</b><br>$%{value:,.0f}<extra></extra>",
                labels=["Spent", "Remaining"],
            )
        ]
    )
    fig.update_layout(
        margin=dict(l=0, r=0, t=0, b=0),
        height=320,
        showlegend=False,
        paper_bgcolor="rgba(0,0,0,0)",
        annotations=[
            dict(
                text=f"<b style='font-size:32px'>${remaining:,.0f}</b><br><span style='font-size:14px; opacity:0.8'>remaining</span>",
                x=0.5,
                y=0.5,
                font=dict(size=16, color="#ffffff"),
                showarrow=False,
                align="center"
            )
        ],
    )
    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

    st.markdown("""
    <h3 style="
        margin-top: 24px;
        margin-bottom: 16px;
        color: #1f2937;
        font-size: 20px;
        font-weight: 600;
    ">Categories</h3>
    """, unsafe_allow_html=True)
    
    spent_by_cat = spent_by_category_for_month(today)

    budgets = {
        "Fun": (settings.get("budget_fun_cents", 0) or 0) / 100.0,
        "groceris": (settings.get("budget_groceris_cents", 0) or 0) / 100.0,
        "travel": (settings.get("budget_travel_cents", 0) or 0) / 100.0,
        "home exp": (settings.get("budget_home_exp_cents", 0) or 0) / 100.0,
        "misc": (settings.get("budget_misc_cents", 0) or 0) / 100.0,
    }
    
    cat_colors = {
        "Fun": "#a855f7",
        "groceris": "#22c55e",
        "travel": "#06b6d4",
        "home exp": "#f59e0b",
        "misc": "#94a3b8",
    }

    for cat in CATEGORIES:
        allocated = float(budgets.get(cat, 0.0) or 0.0)
        used = (spent_by_cat.get(cat, 0) or 0) / 100.0
        remaining_cat = max(allocated - used, 0.0)
        ratio = 0.0 if allocated <= 0 else min(max(used / allocated, 0.0), 1.0)
        
        color = cat_colors.get(cat, "#94a3b8")

        st.markdown(f"""
        <div style="
            background: white;
            padding: 12px 16px;
            border-radius: 12px;
            margin-bottom: 12px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.06);
            border-left: 4px solid {color};
        ">
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
                <span style="font-weight: 600; color: #1f2937;">{category_label(cat)}</span>
                <span style="font-weight: 600; color: #6b7280;">${used:,.0f} / ${allocated:,.0f}</span>
            </div>
        </div>
        """, unsafe_allow_html=True)
        st.progress(ratio)
