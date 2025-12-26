"""Add expense view."""
import datetime as dt
import streamlit as st
from models.expense import insert_expense
from models.tags import list_all_tags, normalize_tags
from utils.constants import CATEGORIES
from utils.helpers import category_label


def render_add():
    """Render add expense tab."""
    st.markdown("""
    <div style="
        background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
        padding: 20px;
        border-radius: 16px;
        margin-bottom: 20px;
        box-shadow: 0 8px 24px rgba(240,147,251,0.25);
    ">
        <h1 style="
            color: white;
            margin: 0;
            font-size: 28px;
            font-weight: 600;
            text-shadow: 0 2px 4px rgba(0,0,0,0.1);
        ">Add Expense</h1>
        <p style="
            color: rgba(255,255,255,0.9);
            margin: 4px 0 0 0;
            font-size: 14px;
        ">Track your spending in seconds</p>
    </div>
    """, unsafe_allow_html=True)

    all_tags = list_all_tags()

    with st.form("add_expense", clear_on_submit=True):
        item_name = st.text_input("Item name", placeholder="e.g., Coffee, Uber, Milk")

        occurred_on = st.date_input("Date", value=dt.date.today())

        c1, c2 = st.columns([1, 1])
        with c1:
            amount = st.number_input("Amount", min_value=0.0, step=1.0, format="%.2f")
        with c2:
            category = st.radio("Category", CATEGORIES, horizontal=True, format_func=category_label)

        st.markdown("---")
        st.markdown("### 🏷️ Tags")
        st.caption("Add tags to categorize this expense (optional)")
        
        tags_selected = st.multiselect(
            "Select or type tags",
            options=all_tags,
            default=[],
            help="Select existing tags or type new ones and press Enter",
            placeholder="e.g., Costco, weekly-shopping, groceries"
        )
        
        custom_tags = st.text_input(
            "Or add new tags (comma-separated)",
            placeholder="e.g., coffee-shop, morning, downtown",
            help="Type multiple tags separated by commas"
        )

        saved = st.form_submit_button("Save", use_container_width=True)

    if saved:
        if not item_name.strip():
            st.error("Please enter an item name.")
        elif amount <= 0:
            st.error("Please enter an amount greater than 0.")
        else:
            final_tags = list(tags_selected)
            if custom_tags.strip():
                new_tags = [t.strip() for t in custom_tags.split(",") if t.strip()]
                final_tags.extend(new_tags)
            
            insert_expense(
                item_name=item_name,
                amount=float(amount),
                category=category,
                occurred_on=occurred_on,
                tags=normalize_tags(final_tags),
            )
            st.success("✅ Saved! Your expense has been recorded.")
