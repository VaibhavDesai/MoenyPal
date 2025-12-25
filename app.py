import os
from sqlalchemy import create_engine, text
import streamlit as st


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


init_db()


TABS = [
    ("dashboard", "Dashboard", "\u25A3"),
    ("daily", "Daily", "\u2630"),
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
<a class="mp-tab mp-tab-add {'active' if is_active else ''}" href="{href}">
  <div class="pill">+</div>
</a>
"""
            )
        else:
            items_html.append(
                f"""
<a class="mp-tab {'active' if is_active else ''}" href="{href}">
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


active_tab = _get_active_tab()

# Top placeholder content for each tab
if active_tab == "dashboard":
    st.title("Dashboard")
    st.write("Overview will live here.")
elif active_tab == "daily":
    st.title("Daily")
    st.write("Daily entries will live here.")
elif active_tab == "add":
    st.title("Add")
    st.write("Quick add flow will live here.")
elif active_tab == "analytics":
    st.title("Analytics")
    st.write("Charts and trends will live here.")
elif active_tab == "settings":
    st.title("Settings")
    st.write("App settings will live here.")

bottom_nav(active_tab)
