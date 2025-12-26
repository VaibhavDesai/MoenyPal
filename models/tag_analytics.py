"""Tag analytics data models."""
from sqlalchemy import text
from .database import get_engine


def tag_spending_over_time(tag_name: str, limit_months: int = 12):
    """Get spending for a specific tag over time (monthly)."""
    engine = get_engine()
    with engine.begin() as conn:
        rows = conn.execute(
            text(
                """
                SELECT substr(e.occurred_at, 1, 7) AS ym,
                       COALESCE(SUM(e.amount_cents), 0) AS total_cents
                FROM expenses e
                JOIN expense_tags et ON et.expense_id = e.id
                JOIN tags t ON t.id = et.tag_id
                WHERE LOWER(t.name) = LOWER(:tag_name)
                GROUP BY ym
                ORDER BY ym DESC
                LIMIT :limit;
                """
            ),
            {"tag_name": tag_name, "limit": limit_months},
        ).mappings()
        return list(reversed(list(rows)))


def top_tags_by_spending(limit: int = 10):
    """Get top tags by total spending."""
    engine = get_engine()
    with engine.begin() as conn:
        rows = conn.execute(
            text(
                """
                SELECT t.name AS tag_name,
                       COALESCE(SUM(e.amount_cents), 0) AS total_cents,
                       COUNT(DISTINCT e.id) AS transaction_count
                FROM tags t
                JOIN expense_tags et ON et.tag_id = t.id
                JOIN expenses e ON e.id = et.expense_id
                GROUP BY t.name
                ORDER BY total_cents DESC
                LIMIT :limit;
                """
            ),
            {"limit": limit},
        ).mappings()
        return list(rows)


def tag_spending_by_month(limit_months: int = 6):
    """Get spending by tag for recent months."""
    engine = get_engine()
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
                SELECT substr(e.occurred_at, 1, 7) AS ym,
                       t.name AS tag_name,
                       COALESCE(SUM(e.amount_cents), 0) AS total_cents
                FROM expenses e
                JOIN expense_tags et ON et.expense_id = e.id
                JOIN tags t ON t.id = et.tag_id
                WHERE substr(e.occurred_at, 1, 7) IN (SELECT ym FROM months)
                GROUP BY ym, t.name
                ORDER BY ym ASC;
                """
            ),
            {"limit": limit_months},
        ).mappings()
        return list(rows)
