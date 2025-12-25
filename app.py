import os
import datetime as dt
import calendar
import csv
import io
from sqlalchemy import create_engine, text
import streamlit as st
import plotly.graph_objects as go


st.set_page_config(page_title="MoneyPal", page_icon="💸", layout="centered")


def _database_url() -> str:
    return os.getenv("DATABASE_URL", "sqlite:///moneypal.db")


@st.cache_resource
def _engine():
    return create_engine(_database_url(), future=True)


def init_db() -> None:
    engine = _engine()
    with engine.begin() as conn:
        conn.execute(
            text(
                """
                CREATE TABLE IF NOT EXISTS expenses (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    amount_cents INTEGER NOT NULL,
                    currency TEXT NOT NULL,
                    category TEXT,
                    note TEXT,
                    occurred_at TEXT NOT NULL,
                    created_at TEXT NOT NULL
                );
                """
            )
        )

        conn.execute(
            text(
                """
                CREATE TABLE IF NOT EXISTS settings (
                    id INTEGER PRIMARY KEY CHECK (id = 1),
                    income_1_cents INTEGER NOT NULL DEFAULT 0,
                    income_2_cents INTEGER NOT NULL DEFAULT 0,
                    saving_goal_pct REAL NOT NULL DEFAULT 0
                );
                """
            )
        )

        existing_cols = {
            r["name"]
            for r in conn.execute(text("PRAGMA table_info(settings);")).mappings().all()
        }
        for col_name in [
            "budget_fun_cents",
            "budget_groceris_cents",
            "budget_travel_cents",
            "budget_home_exp_cents",
            "budget_misc_cents",
        ]:
            if col_name not in existing_cols:
                conn.execute(text(f"ALTER TABLE settings ADD COLUMN {col_name} INTEGER NOT NULL DEFAULT 0;"))

        conn.execute(
            text(
                """
                INSERT OR IGNORE INTO settings (id, income_1_cents, income_2_cents, saving_goal_pct)
                VALUES (1, 0, 0, 0);
                """
            )
        )


init_db()


def get_settings() -> dict:
    engine = _engine()
    with engine.begin() as conn:
        row = (
            conn.execute(
                text(
                    """
                    SELECT income_1_cents, income_2_cents, saving_goal_pct,
                           budget_fun_cents, budget_groceris_cents, budget_travel_cents,
                           budget_home_exp_cents, budget_misc_cents
                    FROM settings
                    WHERE id = 1;
                    """
                )
            )
            .mappings()
            .first()
        )
        if not row:
            return {
                "income_1_cents": 0,
                "income_2_cents": 0,
                "saving_goal_pct": 0.0,
                "budget_fun_cents": 0,
                "budget_groceris_cents": 0,
                "budget_travel_cents": 0,
                "budget_home_exp_cents": 0,
                "budget_misc_cents": 0,
            }
        return dict(row)


def save_settings(
    *,
    income_1: float,
    income_2: float,
    saving_goal_pct: float,
    budget_fun: float,
    budget_groceris: float,
    budget_travel: float,
    budget_home_exp: float,
    budget_misc: float,
) -> None:
    engine = _engine()
    with engine.begin() as conn:
        conn.execute(
            text(
                """
                UPDATE settings
                SET income_1_cents = :income_1_cents,
                    income_2_cents = :income_2_cents,
                    saving_goal_pct = :saving_goal_pct,
                    budget_fun_cents = :budget_fun_cents,
                    budget_groceris_cents = :budget_groceris_cents,
                    budget_travel_cents = :budget_travel_cents,
                    budget_home_exp_cents = :budget_home_exp_cents,
                    budget_misc_cents = :budget_misc_cents
                WHERE id = 1;
                """
            ),
            {
                "income_1_cents": int(round(income_1 * 100)),
                "income_2_cents": int(round(income_2 * 100)),
                "saving_goal_pct": float(saving_goal_pct),
                "budget_fun_cents": int(round(budget_fun * 100)),
                "budget_groceris_cents": int(round(budget_groceris * 100)),
                "budget_travel_cents": int(round(budget_travel * 100)),
                "budget_home_exp_cents": int(round(budget_home_exp * 100)),
                "budget_misc_cents": int(round(budget_misc * 100)),
            },
        )


def get_expense(expense_id: int) -> dict | None:
    engine = _engine()
    with engine.begin() as conn:
        row = conn.execute(
            text(
                """
                SELECT id, occurred_at, note, category, amount_cents
                FROM expenses
                WHERE id = :id;
                """
            ),
            {"id": int(expense_id)},
        ).mappings().first()
        return dict(row) if row else None


def update_expense(*, expense_id: int, item_name: str, amount: float, category: str, occurred_on: dt.date) -> None:
    engine = _engine()
    occurred_at = dt.datetime.combine(occurred_on, dt.time(0, 0, 0)).isoformat()
    with engine.begin() as conn:
        conn.execute(
            text(
                """
                UPDATE expenses
                   SET amount_cents = :amount_cents,
                       category = :category,
                       note = :note,
                       occurred_at = :occurred_at
                 WHERE id = :id;
                """
            ),
            {
                "id": int(expense_id),
                "amount_cents": int(amount * 100),
                "category": category,
                "note": item_name.strip(),
                "occurred_at": occurred_at,
            },
        )


def delete_expense(expense_id: int) -> None:
    engine = _engine()
    with engine.begin() as conn:
        conn.execute(text("DELETE FROM expenses WHERE id = :id;"), {"id": int(expense_id)})


def _recalc_misc_budget() -> None:
    max_budget = float(st.session_state.get("_max_budget", 0.0) or 0.0)
    total_without_misc = (
        float(st.session_state.get("budget_fun", 0.0) or 0.0)
        + float(st.session_state.get("budget_groceris", 0.0) or 0.0)
        + float(st.session_state.get("budget_travel", 0.0) or 0.0)
        + float(st.session_state.get("budget_home_exp", 0.0) or 0.0)
    )
    st.session_state["budget_misc"] = max(max_budget - total_without_misc, 0.0)


def _recalc_budget_from_goal() -> None:
    income_1 = float(st.session_state.get("income_1", 0.0) or 0.0)
    income_2 = float(st.session_state.get("income_2", 0.0) or 0.0)
    saving_goal_pct = float(st.session_state.get("saving_goal_pct", 0.0) or 0.0)
    total_income = income_1 + income_2
    spending_budget = total_income * (1.0 - (saving_goal_pct / 100.0))
    st.session_state["_max_budget"] = max(float(spending_budget), 0.0)
    _recalc_misc_budget()


CATEGORIES = ["Fun", "groceris", "travel", "home exp", "misc"]

CATEGORY_LABELS = {
    "Fun": "Fun",
    "groceris": "Groceries",
    "travel": "Travel",
    "home exp": "Home",
    "misc": "Misc",
}


def _category_label(cat: str) -> str:
    c = (cat or "").strip()
    return CATEGORY_LABELS.get(c, c or "Misc")


TABS = [
    ("dashboard", "Dashboard", "\u25A3"),
    ("transactions", "Transactions", "\u2630"),
    ("add", "", "+"),
    ("analytics", "Analytics", "\u25D4"),
    ("settings", "Settings", "\u2699"),
]


def _get_active_tab() -> str:
    params = st.query_params
    tab = params.get("tab", "dashboard")
    if tab not in {t[0] for t in TABS}:
        tab = "dashboard"
    return tab


def _set_active_tab(tab: str) -> None:
    st.query_params.update({"tab": tab})


def bottom_nav(active: str) -> None:
    st.markdown(
        """
<style>
/* Mobile-first layout tweaks */
main .block-container {
  padding-bottom: 92px; /* space for bottom nav */
  padding-top: 16px;
  max-width: 520px;
}

/* Hide Streamlit default menu/footer for app-like feel */
#MainMenu { visibility: hidden; }
footer { visibility: hidden; }
header { visibility: hidden; }

.mp-bottom-nav {
  position: fixed;
  left: 0;
  right: 0;
  bottom: 0;
  padding: 10px 14px calc(10px + env(safe-area-inset-bottom, 0px));
  background: rgba(255,255,255,0.92);
  backdrop-filter: blur(10px);
  border-top: 1px solid rgba(0,0,0,0.08);
  z-index: 9999;
}

.mp-bottom-nav .inner {
  max-width: 520px;
  margin: 0 auto;
  display: grid;
  grid-template-columns: 1fr 1fr 1fr 1fr 1fr;
  align-items: end;
  gap: 8px;
}

.mp-tab {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 6px 4px;
  border-radius: 12px;
  text-decoration: none;
  color: rgba(0,0,0,0.55);
  font-family: ui-sans-serif, system-ui, -apple-system, Segoe UI, Roboto, Helvetica, Arial;
}

.mp-tab .icon {
  font-size: 18px;
  line-height: 18px;
}

.mp-tab .label {
  margin-top: 4px;
  font-size: 11px;
  line-height: 12px;
}

.mp-tab.active {
  color: #111827;
  font-weight: 600;
}

/* Center + button */
.mp-tab-add {
  transform: translateY(-14px);
}

.mp-tab-add .pill {
  width: 52px;
  height: 52px;
  border-radius: 26px;
  display: grid;
  place-items: center;
  background: #2563eb;
  color: white;
  box-shadow: 0 10px 24px rgba(37,99,235,0.35);
  font-size: 28px;
  line-height: 28px;
}

.mp-tab-add.active .pill {
  background: #1d4ed8;
}

/* Make sure links don't show underline on mobile Safari */
a.mp-tab, a.mp-tab:visited, a.mp-tab:hover, a.mp-tab:active {
  text-decoration: none !important;
}
</style>
        """,
        unsafe_allow_html=True,
    )

    items_html = []
    for tab_id, label, icon in TABS:
        is_active = tab_id == active
        href = f"?tab={tab_id}"

        if tab_id == "add":
            items_html.append(
                f"""
<a class="mp-tab mp-tab-add {'active' if is_active else ''}" href="{href}" target="_self">
  <div class="pill">+</div>
</a>
"""
            )
        else:
            items_html.append(
                f"""
<a class="mp-tab {'active' if is_active else ''}" href="{href}" target="_self">
  <div class="icon">{icon}</div>
  <div class="label">{label}</div>
</a>
"""
            )

    st.markdown(
        """
<div class="mp-bottom-nav">
  <div class="inner">
    {items}
  </div>
</div>
        """.format(items="\n".join(items_html)),
        unsafe_allow_html=True,
    )


def insert_expense(*, item_name: str, amount: float, category: str, occurred_on: dt.date) -> None:
    engine = _engine()
    occurred_at = dt.datetime.combine(occurred_on, dt.time(0, 0, 0)).isoformat()
    created_at = dt.datetime.now().isoformat()
    with engine.begin() as conn:
        conn.execute(
            text(
                """
                INSERT INTO expenses (amount_cents, currency, category, note, occurred_at, created_at)
                VALUES (:amount_cents, :currency, :category, :note, :occurred_at, :created_at);
                """
            ),
            {
                "amount_cents": int(amount * 100),
                "currency": "USD",
                "category": category,
                "note": item_name,
                "occurred_at": occurred_at,
                "created_at": created_at,
            },
        )


def list_recent_expenses(limit: int = 10) -> list:
    engine = _engine()
    with engine.begin() as conn:
        result = conn.execute(
            text(
                """
                SELECT * FROM expenses
                ORDER BY created_at DESC
                LIMIT :limit;
                """
            ),
            {"limit": limit},
        )
        return list(result.mappings())


def _month_window(today: dt.date) -> tuple[str, str]:
    start = dt.datetime(today.year, today.month, 1).isoformat()
    if today.month == 12:
        end = dt.datetime(today.year + 1, 1, 1).isoformat()
    else:
        end = dt.datetime(today.year, today.month + 1, 1).isoformat()
    return start, end


def spent_by_category_for_month(today: dt.date) -> dict:
    start, end = _month_window(today)
    engine = _engine()
    with engine.begin() as conn:
        rows = conn.execute(
            text(
                """
                SELECT category, COALESCE(SUM(amount_cents), 0) AS spent_cents
                FROM expenses
                WHERE occurred_at >= :start AND occurred_at < :end
                GROUP BY category;
                """
            ),
            {"start": start, "end": end},
        ).mappings()
        result = {c: 0 for c in CATEGORIES}
        for r in rows:
            cat = r["category"]
            if cat in result:
                result[cat] = int(r["spent_cents"] or 0)
        return result


def spent_total_for_month(today: dt.date) -> int:
    start, end = _month_window(today)
    engine = _engine()
    with engine.begin() as conn:
        v = conn.execute(
            text(
                """
                SELECT COALESCE(SUM(amount_cents), 0) AS spent_cents
                FROM expenses
                WHERE occurred_at >= :start AND occurred_at < :end;
                """
            ),
            {"start": start, "end": end},
        ).mappings().first()
        return int((v or {}).get("spent_cents", 0) or 0)


def monthly_totals(limit: int = 6):
    engine = _engine()
    with engine.begin() as conn:
        rows = conn.execute(
            text(
                """
                SELECT substr(occurred_at, 1, 7) AS ym,
                       COALESCE(SUM(amount_cents), 0) AS total_cents
                FROM expenses
                GROUP BY ym
                ORDER BY ym DESC
                LIMIT :limit;
                """
            ),
            {"limit": limit},
        ).mappings()
        return list(reversed(list(rows)))


def weekly_totals(limit: int = 8):
    engine = _engine()
    with engine.begin() as conn:
        rows = conn.execute(
            text(
                """
                SELECT strftime('%Y-W%W', substr(occurred_at, 1, 10)) AS yw,
                       COALESCE(SUM(amount_cents), 0) AS total_cents
                FROM expenses
                GROUP BY yw
                ORDER BY yw DESC
                LIMIT :limit;
                """
            ),
            {"limit": limit},
        ).mappings()
        return list(reversed(list(rows)))


def monthly_category_totals(limit_months: int = 6):
    engine = _engine()
    with engine.begin() as conn:
        rows = conn.execute(
            text(
                """
                WITH months AS (
                  SELECT substr(occurred_at, 1, 7) AS ym
                  FROM expenses
                  GROUP BY ym
                  ORDER BY ym DESC
                  LIMIT :limit
                )
                SELECT substr(occurred_at, 1, 7) AS ym,
                       category,
                       COALESCE(SUM(amount_cents), 0) AS total_cents
                FROM expenses
                WHERE substr(occurred_at, 1, 7) IN (SELECT ym FROM months)
                GROUP BY ym, category
                ORDER BY ym ASC;
                """
            ),
            {"limit": limit_months},
        ).mappings()
        return list(rows)


def _format_ym(ym: str) -> str:
    try:
        y, m = ym.split("-")
        return dt.date(int(y), int(m), 1).strftime("%b %Y")
    except Exception:
        return ym


def _format_yw(yw: str) -> str:
    try:
        y, w = yw.split("-W")
        return f"{y} W{int(w):02d}"
    except Exception:
        return yw


def _parse_occurred_at(value: str) -> dt.datetime:
    try:
        return dt.datetime.fromisoformat(value)
    except Exception:
        try:
            return dt.datetime.strptime(value, "%Y-%m-%d %H:%M:%S")
        except Exception:
            return dt.datetime(1970, 1, 1)


def list_transactions(search: str = "", limit: int = 500):
    engine = _engine()
    q = (search or "").strip()
    with engine.begin() as conn:
        if q:
            rows = conn.execute(
                text(
                    """
                    SELECT id, occurred_at, note, category, amount_cents
                    FROM expenses
                    WHERE LOWER(COALESCE(note, '')) LIKE :q
                       OR LOWER(COALESCE(category, '')) LIKE :q
                    ORDER BY occurred_at DESC, id DESC
                    LIMIT :limit;
                    """
                ),
                {"q": f"%{q.lower()}%", "limit": limit},
            ).mappings()
        else:
            rows = conn.execute(
                text(
                    """
                    SELECT id, occurred_at, note, category, amount_cents
                    FROM expenses
                    ORDER BY occurred_at DESC, id DESC
                    LIMIT :limit;
                    """
                ),
                {"limit": limit},
            ).mappings()
        return list(rows)


def reset_all_data() -> None:
    engine = _engine()
    with engine.begin() as conn:
        conn.execute(text("DELETE FROM expenses;"))
        conn.execute(
            text(
                """
                UPDATE settings
                SET income_1_cents = 0,
                    income_2_cents = 0,
                    saving_goal_pct = 0,
                    budget_fun_cents = 0,
                    budget_groceris_cents = 0,
                    budget_travel_cents = 0,
                    budget_home_exp_cents = 0,
                    budget_misc_cents = 0
                WHERE id = 1;
                """
            )
        )


active_tab = _get_active_tab()

# Top placeholder content for each tab
if active_tab == "dashboard":
    today = dt.date.today()
    last_day = calendar.monthrange(today.year, today.month)[1]
    days_remaining = last_day - today.day
    st.title(f"{days_remaining} days remaining")

    settings = get_settings()
    income_1 = (settings.get("income_1_cents", 0) or 0) / 100.0
    income_2 = (settings.get("income_2_cents", 0) or 0) / 100.0
    saving_goal_pct = float(settings.get("saving_goal_pct", 0.0) or 0.0)
    total_income = float(income_1) + float(income_2)
    spending_budget = total_income * (1.0 - (saving_goal_pct / 100.0))

    spent_cents = spent_total_for_month(today)
    spent = spent_cents / 100.0
    remaining = max(spending_budget - spent, 0.0)

    budget = max(spending_budget, 0.0)
    spent_clamped = min(max(spent, 0.0), budget) if budget > 0 else 0.0
    remaining_clamped = max(budget - spent_clamped, 0.0)

    fig = go.Figure(
        data=[
            go.Pie(
                values=[spent_clamped, remaining_clamped],
                hole=0.72,
                sort=False,
                direction="clockwise",
                rotation=90,
                marker={"colors": ["#ef4444", "#22c55e"]},
                textinfo="none",
                hovertemplate="%{label}: %{value:.2f}<extra></extra>",
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
                text=f"<b>{remaining:,.0f}</b><br>left",
                x=0.5,
                y=0.5,
                font=dict(size=26, color="#ffffff"),
                showarrow=False,
            )
        ],
    )
    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

    st.markdown("### Categories")
    spent_by_cat = spent_by_category_for_month(today)

    budgets = {
        "Fun": (settings.get("budget_fun_cents", 0) or 0) / 100.0,
        "groceris": (settings.get("budget_groceris_cents", 0) or 0) / 100.0,
        "travel": (settings.get("budget_travel_cents", 0) or 0) / 100.0,
        "home exp": (settings.get("budget_home_exp_cents", 0) or 0) / 100.0,
        "misc": (settings.get("budget_misc_cents", 0) or 0) / 100.0,
    }

    for cat in CATEGORIES:
        allocated = float(budgets.get(cat, 0.0) or 0.0)
        used = (spent_by_cat.get(cat, 0) or 0) / 100.0
        remaining_cat = max(allocated - used, 0.0)
        ratio = 0.0 if allocated <= 0 else min(max(used / allocated, 0.0), 1.0)

        h1, h2 = st.columns([3, 1])
        with h1:
            st.markdown(f"**{_category_label(cat)}**")
        with h2:
            st.markdown(f"**{used:,.0f}/{allocated:,.0f}**")
        st.progress(ratio)
elif active_tab == "add":
    st.title("Add quick expense")
    st.caption("Add a purchase in a few seconds.")

    with st.form("add_expense", clear_on_submit=True):
        item_name = st.text_input("Item name", placeholder="e.g., Coffee, Uber, Milk")

        occurred_on = st.date_input("Date", value=dt.date.today())

        c1, c2 = st.columns([1, 1])
        with c1:
            amount = st.number_input("Amount", min_value=0.0, step=1.0, format="%.2f")
        with c2:
            category = st.radio("Category", CATEGORIES, horizontal=True, format_func=_category_label)

        saved = st.form_submit_button("Save")

    if saved:
        if not item_name.strip():
            st.error("Please enter an item name.")
        elif amount <= 0:
            st.error("Please enter an amount greater than 0.")
        else:
            insert_expense(item_name=item_name, amount=float(amount), category=category, occurred_on=occurred_on)
            st.success("Saved")
elif active_tab == "transactions":
    st.title("Transactions")
    search = st.text_input("Search", placeholder="Search by item or category")

    rows = list_transactions(search=search, limit=1000)
    if not rows:
        st.caption("No transactions.")
    else:
        groups: dict[str, list[dict]] = {}
        for r in rows:
            occurred = _parse_occurred_at(r.get("occurred_at") or "")
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

                c1, c2, c3, c4 = st.columns([1.2, 2.2, 1.0, 1.2])
                with c1:
                    st.caption(d)
                with c2:
                    st.write(f"**{note}**")
                    st.caption(_category_label(category))
                with c3:
                    st.write(f"{amount:,.2f}")
                with c4:
                    edit_clicked = st.button("Edit", key=f"edit_{expense_id}")
                    delete_clicked = st.button("Delete", key=f"delete_{expense_id}")

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
                            occurred_dt = _parse_occurred_at(existing.get("occurred_at") or "")
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
                                format_func=_category_label,
                                key=f"edit_category_{expense_id}",
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
                                update_expense(
                                    expense_id=expense_id,
                                    item_name=str(edit_item),
                                    amount=float(edit_amount),
                                    category=str(edit_category),
                                    occurred_on=edit_date,
                                )
                                st.session_state.pop("_editing_expense_id", None)
                                st.rerun()
elif active_tab == "analytics":
    st.title("Analytics")

    mom = monthly_totals(limit=8)
    wow = weekly_totals(limit=10)
    mom_cat = monthly_category_totals(limit_months=8)

    if not mom and not wow:
        st.caption("No data yet. Add a few expenses to see analytics.")
    else:
        if mom:
            x = [_format_ym(r["ym"]) for r in mom]
            y = [(int(r["total_cents"] or 0) / 100.0) for r in mom]

            st.markdown("### Month over month")

            fig_mom = go.Figure(
                data=[
                    go.Scatter(
                        x=x,
                        y=y,
                        mode="lines+markers",
                        line=dict(color="#3b82f6", width=3),
                        marker=dict(size=7),
                        fill="tozeroy",
                        fillcolor="rgba(59,130,246,0.18)",
                        hovertemplate="%{x}: %{y:.2f}<extra></extra>",
                    )
                ]
            )
            fig_mom.update_layout(
                template="plotly_dark",
                margin=dict(l=10, r=10, t=10, b=10),
                height=260,
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)",
                xaxis=dict(type="category", tickangle=0, tickfont=dict(size=10)),
                yaxis=dict(title="", gridcolor="rgba(255,255,255,0.10)"),
            )
            st.plotly_chart(fig_mom, use_container_width=True, config={"displayModeBar": False})

        if mom_cat:
            months = sorted({r["ym"] for r in mom_cat})
            months_fmt = [_format_ym(m) for m in months]
            by_cat: dict[str, dict[str, float]] = {c: {m: 0.0 for m in months} for c in CATEGORIES}
            for r in mom_cat:
                cat = r.get("category") or "misc"
                if cat not in by_cat:
                    continue
                by_cat[cat][r["ym"]] = float(int(r.get("total_cents") or 0) / 100.0)

            st.markdown("### Monthly categories")

            colors = {
                "Fun": "#a855f7",
                "groceris": "#22c55e",
                "travel": "#06b6d4",
                "home exp": "#f59e0b",
                "misc": "#94a3b8",
            }

            fig_area = go.Figure()
            first = True
            for cat in CATEGORIES:
                fig_area.add_trace(
                    go.Scatter(
                        name=_category_label(cat),
                        x=months_fmt,
                        y=[by_cat[cat][m] for m in months],
                        mode="lines",
                        line=dict(color=colors.get(cat, "#94a3b8"), width=2),
                        stackgroup="one",
                        groupnorm="",
                        fill="tonexty" if not first else "tozeroy",
                        hovertemplate=f"{_category_label(cat)} %{x}: %{{y:.2f}}<extra></extra>",
                    )
                )
                first = False

            fig_area.update_layout(
                template="plotly_dark",
                margin=dict(l=10, r=10, t=10, b=10),
                height=320,
                showlegend=True,
                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0, font=dict(size=10)),
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)",
                xaxis=dict(type="category", tickangle=0, tickfont=dict(size=10)),
                yaxis=dict(title="", gridcolor="rgba(255,255,255,0.10)"),
            )
            st.plotly_chart(fig_area, use_container_width=True, config={"displayModeBar": False})

        if wow:
            x = [_format_yw(r["yw"]) for r in wow]
            y = [(int(r["total_cents"] or 0) / 100.0) for r in wow]

            st.markdown("### Week over week")
            fig_wow = go.Figure(
                data=[
                    go.Scatter(
                        x=x,
                        y=y,
                        mode="lines+markers",
                        line=dict(color="#ef4444", width=3),
                        marker=dict(size=7),
                        fill="tozeroy",
                        fillcolor="rgba(239,68,68,0.12)",
                        hovertemplate="%{x}: %{y:.2f}<extra></extra>",
                    )
                ]
            )
            fig_wow.update_layout(
                template="plotly_dark",
                margin=dict(l=10, r=10, t=10, b=10),
                height=260,
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)",
                xaxis=dict(type="category", tickangle=0, tickfont=dict(size=10)),
                yaxis=dict(title="", gridcolor="rgba(255,255,255,0.10)"),
            )
            st.plotly_chart(fig_wow, use_container_width=True, config={"displayModeBar": False})
elif active_tab == "settings":
    st.title("Settings")
    st.markdown("### Goal")

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
            _category_label("Fun"),
            min_value=0.0,
            max_value=slider_max_budget,
            step=10.0,
            key="budget_fun",
            on_change=_recalc_misc_budget,
            disabled=budgets_disabled,
        )
        st.slider(
            _category_label("travel"),
            min_value=0.0,
            max_value=slider_max_budget,
            step=10.0,
            key="budget_travel",
            on_change=_recalc_misc_budget,
            disabled=budgets_disabled,
        )
    with b2:
        st.slider(
            _category_label("groceris"),
            min_value=0.0,
            max_value=slider_max_budget,
            step=10.0,
            key="budget_groceris",
            on_change=_recalc_misc_budget,
            disabled=budgets_disabled,
        )
        st.slider(
            _category_label("home exp"),
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
        _category_label("misc"),
        min_value=0.0,
        max_value=slider_max_budget,
        step=10.0,
        key="budget_misc",
        disabled=True,
    )

    if budgets_disabled:
        st.caption("Set your Income and % saving goal above to unlock category budgets.")

    _, cb, _ = st.columns([4, 2, 4])
    with cb:
        save_clicked = st.button("Save goal")

    if save_clicked:
        if allocated_without_misc > max_budget:
            st.error("Fix category budgets before saving.")
        else:
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
        occurred = _parse_occurred_at(r.get("occurred_at") or "")
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

bottom_nav(active_tab)
