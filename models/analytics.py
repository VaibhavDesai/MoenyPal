"""Analytics data models."""
import datetime as dt
from sqlalchemy import text
from .database import get_engine


def monthly_totals(limit: int = 6, start_date: dt.date | None = None, end_date: dt.date | None = None, search: str = ""):
    """Get monthly spending totals with optional filters."""
    engine = get_engine()
    
    where_parts = []
    params = {"limit": limit}
    
    if start_date:
        where_parts.append("occurred_at >= :start")
        params["start"] = dt.datetime.combine(start_date, dt.time(0, 0, 0)).isoformat()
    
    if end_date:
        where_parts.append("occurred_at < :end")
        end_excl = dt.datetime.combine(end_date + dt.timedelta(days=1), dt.time(0, 0, 0)).isoformat()
        params["end"] = end_excl
    
    if search:
        where_parts.append("(LOWER(COALESCE(note, '')) LIKE :q OR LOWER(COALESCE(category, '')) LIKE :q)")
        params["q"] = f"%{search.lower()}%"
    
    where_sql = " AND ".join(where_parts) if where_parts else "1=1"
    
    with engine.begin() as conn:
        rows = conn.execute(
            text(
                f"""
                SELECT substr(occurred_at, 1, 7) AS ym,
                       COALESCE(SUM(amount_cents), 0) AS total_cents
                FROM expenses
                WHERE {where_sql}
                GROUP BY ym
                ORDER BY ym DESC
                LIMIT :limit;
                """
            ),
            params,
        ).mappings()
        return list(reversed(list(rows)))


def weekly_totals(limit: int = 10):
    """Get weekly spending totals."""
    engine = get_engine()
    with engine.begin() as conn:
        rows = conn.execute(
            text(
                """
                SELECT strftime('%Y-W%W', occurred_at) AS yw,
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


def monthly_category_totals(limit_months: int = 6, start_date: dt.date | None = None, end_date: dt.date | None = None):
    """Get monthly spending by category with optional filters."""
    engine = get_engine()
    
    where_parts = []
    params = {"limit": limit_months}
    
    if start_date:
        where_parts.append("occurred_at >= :start")
        params["start"] = dt.datetime.combine(start_date, dt.time(0, 0, 0)).isoformat()
    
    if end_date:
        where_parts.append("occurred_at < :end")
        end_excl = dt.datetime.combine(end_date + dt.timedelta(days=1), dt.time(0, 0, 0)).isoformat()
        params["end"] = end_excl
    
    where_sql = " AND ".join(where_parts) if where_parts else "1=1"
    
    with engine.begin() as conn:
        rows = conn.execute(
            text(
                f"""
                WITH months AS (
                  SELECT substr(occurred_at, 1, 7) AS ym
                  FROM expenses
                  WHERE {where_sql}
                  GROUP BY ym
                  ORDER BY ym DESC
                  LIMIT :limit
                )
                SELECT substr(occurred_at, 1, 7) AS ym,
                       category,
                       COALESCE(SUM(amount_cents), 0) AS total_cents
                FROM expenses
                WHERE substr(occurred_at, 1, 7) IN (SELECT ym FROM months)
                  AND {where_sql}
                GROUP BY ym, category
                ORDER BY ym ASC;
                """
            ),
            params,
        ).mappings()
        return list(rows)


def get_kpi_metrics(start_date: dt.date | None = None, end_date: dt.date | None = None, search: str = ""):
    """Get KPI metrics for analytics dashboard."""
    engine = get_engine()
    
    where_parts = []
    params = {}
    
    if start_date:
        where_parts.append("occurred_at >= :start")
        params["start"] = dt.datetime.combine(start_date, dt.time(0, 0, 0)).isoformat()
    
    if end_date:
        where_parts.append("occurred_at < :end")
        end_excl = dt.datetime.combine(end_date + dt.timedelta(days=1), dt.time(0, 0, 0)).isoformat()
        params["end"] = end_excl
    
    if search:
        where_parts.append("(LOWER(COALESCE(note, '')) LIKE :q OR LOWER(COALESCE(category, '')) LIKE :q)")
        params["q"] = f"%{search.lower()}%"
    
    where_sql = " AND ".join(where_parts) if where_parts else "1=1"
    
    with engine.begin() as conn:
        result = conn.execute(
            text(
                f"""
                SELECT 
                    COALESCE(SUM(amount_cents), 0) AS total_cents,
                    COUNT(*) AS transaction_count,
                    COALESCE(AVG(amount_cents), 0) AS avg_cents,
                    MIN(occurred_at) AS first_date,
                    MAX(occurred_at) AS last_date
                FROM expenses
                WHERE {where_sql};
                """
            ),
            params,
        ).mappings().first()
        
        return dict(result) if result else {
            "total_cents": 0,
            "transaction_count": 0,
            "avg_cents": 0,
            "first_date": None,
            "last_date": None,
        }
