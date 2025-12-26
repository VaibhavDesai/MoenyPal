"""Transactions view."""
import datetime as dt
import streamlit as st
from models.expense import list_transactions, get_expense, update_expense, delete_expense
from models.tags import list_all_tags, normalize_tags
from utils.constants import CATEGORIES
from utils.helpers import category_label, parse_occurred_at


def render_transactions():
    """Render transactions tab."""
    st.markdown("""
    <div style="
        background: linear-gradient(135deg, #4facfe 0%, #00f2fe 100%);
        padding: 20px;
        border-radius: 16px;
        margin-bottom: 20px;
        box-shadow: 0 8px 24px rgba(79,172,254,0.25);
    ">
        <h1 style="
            color: white;
            margin: 0;
            font-size: 28px;
            font-weight: 600;
            text-shadow: 0 2px 4px rgba(0,0,0,0.1);
        ">Transactions</h1>
        <p style="
            color: rgba(255,255,255,0.9);
            margin: 4px 0 0 0;
            font-size: 14px;
        ">View and manage your expenses</p>
    </div>
    """, unsafe_allow_html=True)
    all_tags = list_all_tags()

    f1, f2 = st.columns([1, 1])
    with f1:
        dr = st.date_input(
            "Date range",
            value=(dt.date.today().replace(day=1), dt.date.today()),
        )
    with f2:
        tag_choice = st.selectbox(
            "Tag",
            options=[""] + all_tags,
            format_func=lambda v: ("All" if not v else v),
        )

    search = st.text_input("Search", placeholder="Search by item, category, or tag")

    start_date = None
    end_date = None
    if isinstance(dr, tuple) and len(dr) == 2:
        start_date, end_date = dr

    rows = list_transactions(search=search, limit=1000, start_date=start_date, end_date=end_date, tag=(tag_choice or None))
    if not rows:
        st.caption("No transactions.")
    else:
        groups: dict[str, list[dict]] = {}
        for r in rows:
            occurred = parse_occurred_at(r.get("occurred_at") or "")
            key = occurred.strftime("%B %Y")
            groups.setdefault(key, []).append({**dict(r), "_occurred": occurred})

        for month_label, items in groups.items():
            subtotal_cents = sum(int(i.get("amount_cents") or 0) for i in items)
            st.markdown(f"### {month_label}")
            st.caption(f"Subtotal: {(subtotal_cents / 100.0):,.2f}")

            for i in items:
                expense_id = int(i.get("id") or 0)
                d = i["_occurred"].date().isoformat()
                note = (i.get("note") or "").strip() or "(no item)"
                category = (i.get("category") or "misc").strip()
                amount = (int(i.get("amount_cents") or 0) / 100.0)
                tags_text = (i.get("tags") or "").strip()

                c1, c2, c3, c4 = st.columns([1.2, 2.3, 0.9, 0.9])
                with c1:
                    st.caption(d)
                with c2:
                    st.write(f"**{note}**")
                    if tags_text:
                        st.caption(f"{category_label(category)} · {tags_text}")
                    else:
                        st.caption(category_label(category))
                with c3:
                    st.write(f"{amount:,.2f}")
                with c4:
                    a1, a2 = st.columns([1, 1], gap="small")
                    with a1:
                        edit_clicked = st.button(
                            "✏️",
                            key=f"edit_{expense_id}",
                            help="Edit",
                            use_container_width=True,
                        )
                    with a2:
                        delete_clicked = st.button(
                            "🗑️",
                            key=f"delete_{expense_id}",
                            help="Delete",
                            use_container_width=True,
                        )

                if edit_clicked:
                    st.session_state["_editing_expense_id"] = expense_id

                if delete_clicked:
                    st.session_state["_deleting_expense_id"] = expense_id

                if st.session_state.get("_deleting_expense_id") == expense_id:
                    dc1, dc2, _ = st.columns([1, 1, 3])
                    with dc1:
                        if st.button("Confirm delete", key=f"confirm_delete_{expense_id}"):
                            delete_expense(expense_id)
                            st.session_state.pop("_deleting_expense_id", None)
                            st.session_state.pop("_editing_expense_id", None)
                            st.rerun()
                    with dc2:
                        if st.button("Cancel", key=f"cancel_delete_{expense_id}"):
                            st.session_state.pop("_deleting_expense_id", None)

                if st.session_state.get("_editing_expense_id") == expense_id:
                    existing = get_expense(expense_id)
                    if existing:
                        with st.form(f"edit_form_{expense_id}"):
                            st.caption("Edit transaction")
                            occurred_dt = parse_occurred_at(existing.get("occurred_at") or "")
                            edit_date = st.date_input(
                                "Date",
                                value=occurred_dt.date(),
                                key=f"edit_date_{expense_id}",
                            )
                            edit_item = st.text_input(
                                "Item",
                                value=(existing.get("note") or "").strip(),
                                key=f"edit_item_{expense_id}",
                            )
                            edit_amount = st.number_input(
                                "Amount",
                                min_value=0.0,
                                step=1.0,
                                format="%.2f",
                                value=(int(existing.get("amount_cents") or 0) / 100.0),
                                key=f"edit_amount_{expense_id}",
                            )
                            edit_category = st.selectbox(
                                "Category",
                                options=CATEGORIES,
                                index=CATEGORIES.index((existing.get("category") or "misc").strip())
                                if (existing.get("category") or "misc").strip() in CATEGORIES
                                else CATEGORIES.index("misc"),
                                format_func=category_label,
                                key=f"edit_category_{expense_id}",
                            )

                            existing_tags = list(existing.get("tags") or [])
                            edit_tags_selected = st.multiselect(
                                "Tags",
                                options=all_tags,
                                default=[t for t in existing_tags if t in all_tags],
                                key=f"edit_tags_{expense_id}",
                            )
                            edit_custom_tags = st.text_input(
                                "Or add new tags (comma-separated)",
                                value=", ".join([t for t in existing_tags if t not in all_tags]),
                                key=f"edit_custom_tags_{expense_id}",
                                placeholder="Comma separated",
                            )

                            ec1, ec2 = st.columns([1, 1])
                            with ec1:
                                submitted = st.form_submit_button("Save")
                            with ec2:
                                cancel = st.form_submit_button("Cancel")

                        if cancel:
                            st.session_state.pop("_editing_expense_id", None)
                            st.rerun()

                        if submitted:
                            if not (edit_item or "").strip():
                                st.error("Please enter an item name.")
                            elif float(edit_amount) <= 0:
                                st.error("Please enter an amount greater than 0.")
                            else:
                                final_tags = list(edit_tags_selected)
                                if edit_custom_tags.strip():
                                    new_tags = [t.strip() for t in edit_custom_tags.split(",") if t.strip()]
                                    final_tags.extend(new_tags)
                                
                                update_expense(
                                    expense_id=expense_id,
                                    item_name=str(edit_item),
                                    amount=float(edit_amount),
                                    category=str(edit_category),
                                    occurred_on=edit_date,
                                    tags=normalize_tags(final_tags),
                                )
                                st.session_state.pop("_editing_expense_id", None)
                                st.rerun()
