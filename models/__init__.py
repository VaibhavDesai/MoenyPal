"""Models package for database interactions and business logic."""
from .database import init_db, get_engine
from .expense import (
    insert_expense,
    get_expense,
    update_expense,
    delete_expense,
    list_transactions,
    spent_by_category_for_month,
    spent_total_for_month,
)
from .settings import get_settings, save_settings
from .tags import list_all_tags, normalize_tags
from .analytics import monthly_totals, weekly_totals, monthly_category_totals, get_kpi_metrics, monthly_savings_rate
from .tag_analytics import tag_spending_over_time, top_tags_by_spending, tag_spending_by_month

__all__ = [
    "init_db",
    "get_engine",
    "insert_expense",
    "get_expense",
    "update_expense",
    "delete_expense",
    "list_transactions",
    "spent_by_category_for_month",
    "spent_total_for_month",
    "get_settings",
    "save_settings",
    "list_all_tags",
    "normalize_tags",
    "monthly_totals",
    "weekly_totals",
    "monthly_category_totals",
    "get_kpi_metrics",
    "monthly_savings_rate",
    "tag_spending_over_time",
    "top_tags_by_spending",
    "tag_spending_by_month",
]
