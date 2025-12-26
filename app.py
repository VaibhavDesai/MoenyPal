"""MoneyPal - Mobile-first expense tracking application.

This is the main entry point that orchestrates the MVC architecture.
"""
import streamlit as st
from pathlib import Path
from models.database import init_db
from views import (
    render_dashboard,
    render_add,
    render_transactions,
    render_analytics,
    render_settings,
    render_bottom_nav,
)

# Configure Streamlit page
st.set_page_config(
    page_title="MoneyPal",
    page_icon=".streamlit/favicon.svg",
    layout="centered"
)

# Initialize database
init_db()


def get_active_tab() -> str:
    """Get active tab from query parameters."""
    params = st.query_params
    tab = params.get("tab", "dashboard")
    valid_tabs = {"dashboard", "transactions", "add", "analytics", "settings"}
    if tab not in valid_tabs:
        tab = "dashboard"
    return tab


def main():
    """Main application entry point."""
    active_tab = get_active_tab()

    # Route to appropriate view based on active tab
    if active_tab == "dashboard":
        render_dashboard()
    elif active_tab == "add":
        render_add()
    elif active_tab == "transactions":
        render_transactions()
    elif active_tab == "analytics":
        render_analytics()
    elif active_tab == "settings":
        render_settings()

    # Render bottom navigation
    render_bottom_nav(active_tab)


if __name__ == "__main__":
    main()
