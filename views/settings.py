"""Settings view."""
import csv
import io
import streamlit as st
from models.settings import get_settings, save_settings
from models.expense import list_transactions
from models.database import reset_all_data
from utils.constants import CATEGORIES
from utils.helpers import category_label, parse_occurred_at


def _recalc_misc_budget() -> None:
    """Recalculate misc budget based on other categories."""
    max_budget = float(st.session_state.get("_max_budget", 0.0) or 0.0)
    total_without_misc = (
        float(st.session_state.get("budget_fun", 0.0) or 0.0)
        + float(st.session_state.get("budget_groceris", 0.0) or 0.0)
        + float(st.session_state.get("budget_travel", 0.0) or 0.0)
        + float(st.session_state.get("budget_home_exp", 0.0) or 0.0)
    )
    st.session_state["budget_misc"] = max(max_budget - total_without_misc, 0.0)


def _recalc_budget_from_goal() -> None:
    """Recalculate spending budget from income and savings goal."""
    income_1 = float(st.session_state.get("income_1", 0.0) or 0.0)
    income_2 = float(st.session_state.get("income_2", 0.0) or 0.0)
    saving_goal_pct = float(st.session_state.get("saving_goal_pct", 0.0) or 0.0)
    total_income = income_1 + income_2
    spending_budget = total_income * (1.0 - (saving_goal_pct / 100.0))
    st.session_state["_max_budget"] = max(float(spending_budget), 0.0)
    _recalc_misc_budget()


def render_settings():
    """Render settings tab."""
    st.markdown("""
    <div style="
        background: linear-gradient(135deg, #fa709a 0%, #fee140 100%);
        padding: 20px;
        border-radius: 16px;
        margin-bottom: 20px;
        box-shadow: 0 8px 24px rgba(250,112,154,0.25);
    ">
        <h1 style="
            color: white;
            margin: 0;
            font-size: 28px;
            font-weight: 600;
            text-shadow: 0 2px 4px rgba(0,0,0,0.1);
        ">Settings</h1>
        <p style="
            color: rgba(255,255,255,0.9);
            margin: 4px 0 0 0;
            font-size: 14px;
        ">Configure your budget and goals</p>
    </div>
    """, unsafe_allow_html=True)
    
    st.markdown("""
    <h3 style="
        margin-top: 8px;
        margin-bottom: 16px;
        color: #1f2937;
        font-size: 18px;
        font-weight: 600;
    ">💰 Goal</h3>
    """, unsafe_allow_html=True)

    current = get_settings()
    income_1_default = (current.get("income_1_cents", 0) or 0) / 100.0
    income_2_default = (current.get("income_2_cents", 0) or 0) / 100.0
    saving_goal_default = float(current.get("saving_goal_pct", 0.0) or 0.0)
    budget_fun_default = (current.get("budget_fun_cents", 0) or 0) / 100.0
    budget_groceris_default = (current.get("budget_groceris_cents", 0) or 0) / 100.0
    budget_travel_default = (current.get("budget_travel_cents", 0) or 0) / 100.0
    budget_home_exp_default = (current.get("budget_home_exp_cents", 0) or 0) / 100.0
    budget_misc_default = (current.get("budget_misc_cents", 0) or 0) / 100.0

    if "income_1" not in st.session_state:
        st.session_state["income_1"] = float(income_1_default)
    if "income_2" not in st.session_state:
        st.session_state["income_2"] = float(income_2_default)
    if "saving_goal_pct" not in st.session_state:
        st.session_state["saving_goal_pct"] = int(round(saving_goal_default))
    if "budget_fun" not in st.session_state:
        st.session_state["budget_fun"] = float(budget_fun_default)
    if "budget_groceris" not in st.session_state:
        st.session_state["budget_groceris"] = float(budget_groceris_default)
    if "budget_travel" not in st.session_state:
        st.session_state["budget_travel"] = float(budget_travel_default)
    if "budget_home_exp" not in st.session_state:
        st.session_state["budget_home_exp"] = float(budget_home_exp_default)
    if "budget_misc" not in st.session_state:
        st.session_state["budget_misc"] = float(budget_misc_default)

    c1, c2 = st.columns([1, 1])
    with c1:
        income_1 = st.number_input(
            "Income 1",
            min_value=0.0,
            step=100.0,
            key="income_1",
            format="%.2f",
            on_change=_recalc_budget_from_goal,
        )
    with c2:
        income_2 = st.number_input(
            "Income 2",
            min_value=0.0,
            step=100.0,
            key="income_2",
            format="%.2f",
            on_change=_recalc_budget_from_goal,
        )

    total_income = float(income_1) + float(income_2)
    st.metric("Total income", f"{total_income:,.2f}")

    saving_goal_pct = st.slider(
        "% saving goal",
        min_value=0,
        max_value=100,
        step=1,
        key="saving_goal_pct",
        on_change=_recalc_budget_from_goal,
    )
    spending_budget = total_income * (1.0 - (float(saving_goal_pct) / 100.0))
    st.metric("Spending budget", f"{spending_budget:,.2f}")

    st.markdown("#### Category budgets")
    st.caption("Budgets are allocated from your spending budget. Any remaining amount is automatically assigned to misc.")

    max_budget = max(float(spending_budget), 0.0)
    slider_max_budget = max(max_budget, 1.0)
    budgets_disabled = max_budget <= 0.0
    st.session_state["_max_budget"] = max_budget
    _recalc_misc_budget()

    b1, b2 = st.columns([1, 1])
    with b1:
        st.slider(
            category_label("Fun"),
            min_value=0.0,
            max_value=slider_max_budget,
            step=10.0,
            key="budget_fun",
            on_change=_recalc_misc_budget,
            disabled=budgets_disabled,
        )
        st.slider(
            category_label("travel"),
            min_value=0.0,
            max_value=slider_max_budget,
            step=10.0,
            key="budget_travel",
            on_change=_recalc_misc_budget,
            disabled=budgets_disabled,
        )
    with b2:
        st.slider(
            category_label("groceris"),
            min_value=0.0,
            max_value=slider_max_budget,
            step=10.0,
            key="budget_groceris",
            on_change=_recalc_misc_budget,
            disabled=budgets_disabled,
        )
        st.slider(
            category_label("home exp"),
            min_value=0.0,
            max_value=slider_max_budget,
            step=10.0,
            key="budget_home_exp",
            on_change=_recalc_misc_budget,
            disabled=budgets_disabled,
        )

    allocated_without_misc = (
        float(st.session_state.get("budget_fun", 0.0) or 0.0)
        + float(st.session_state.get("budget_groceris", 0.0) or 0.0)
        + float(st.session_state.get("budget_travel", 0.0) or 0.0)
        + float(st.session_state.get("budget_home_exp", 0.0) or 0.0)
    )
    if allocated_without_misc > max_budget:
        st.error("Category allocations exceed your spending budget. Reduce a category slider.")
    else:
        _recalc_misc_budget()

    st.slider(
        category_label("misc"),
        min_value=0.0,
        max_value=slider_max_budget,
        step=10.0,
        key="budget_misc",
        disabled=True,
    )

    if budgets_disabled:
        st.caption("Set your Income and % saving goal above to unlock category budgets.")

    st.markdown("---")
    s1, s2 = st.columns([1, 1])
    with s1:
        if st.button("Calculate", use_container_width=True):
            _recalc_budget_from_goal()
            st.success("Recalculated!")
    with s2:
        if st.button("Save", use_container_width=True):
            save_settings(
                income_1=float(st.session_state["income_1"]),
                income_2=float(st.session_state["income_2"]),
                saving_goal_pct=float(st.session_state["saving_goal_pct"]),
                budget_fun=float(st.session_state["budget_fun"]),
                budget_groceris=float(st.session_state["budget_groceris"]),
                budget_travel=float(st.session_state["budget_travel"]),
                budget_home_exp=float(st.session_state["budget_home_exp"]),
                budget_misc=float(st.session_state["budget_misc"]),
            )
            st.success("Saved")

    st.markdown("### Export")
    export_rows = list_transactions(search="", limit=100000)
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(["date", "item", "category", "price"])
    for r in export_rows:
        occurred = parse_occurred_at(r.get("occurred_at") or "")
        d = occurred.date().isoformat()
        note = (r.get("note") or "").strip()
        category = (r.get("category") or "").strip()
        amount = (int(r.get("amount_cents") or 0) / 100.0)
        writer.writerow([d, note, category, f"{amount:.2f}"])

    st.download_button(
        "Export CSV",
        data=buf.getvalue().encode("utf-8"),
        file_name="moneypal-transactions.csv",
        mime="text/csv",
    )

    st.markdown("### Reset")
    st.caption("This will permanently delete all transactions and reset your settings.")
    confirm = st.text_input("Type RESET to confirm", value="")
    if st.button("Reset all data"):
        if confirm.strip() != "RESET":
            st.error("Type RESET to confirm.")
        else:
            reset_all_data()
            for k in [
                "income_1",
                "income_2",
                "saving_goal_pct",
                "budget_fun",
                "budget_groceris",
                "budget_travel",
                "budget_home_exp",
                "budget_misc",
                "_max_budget",
            ]:
                if k in st.session_state:
                    del st.session_state[k]
            st.success("All data deleted.")
            st.rerun()
