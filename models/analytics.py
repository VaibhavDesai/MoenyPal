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


def monthly_savings_rate(limit: int = 12):
    """Get monthly savings rate (%) based on income and spending."""
    engine = get_engine()
    
    with engine.begin() as conn:
        # Get settings for income calculation
        settings_row = conn.execute(
            text("SELECT income_1_cents, income_2_cents FROM settings WHERE id = 1;")
        ).mappings().first()
        
        if not settings_row:
            return []
        
        income_1_cents = int(settings_row.get("income_1_cents", 0) or 0)
        income_2_cents = int(settings_row.get("income_2_cents", 0) or 0)
        total_income_cents = income_1_cents + income_2_cents
        
        if total_income_cents <= 0:
            return []
        
        # Get monthly spending
        rows = conn.execute(
            text(
                """
                SELECT substr(occurred_at, 1, 7) AS ym,
                       COALESCE(SUM(amount_cents), 0) AS spent_cents
                FROM expenses
                GROUP BY ym
                ORDER BY ym DESC
                LIMIT :limit;
                """
            ),
            {"limit": limit},
        ).mappings()
        
        results = []
        for row in rows:
            spent_cents = int(row.get("spent_cents", 0) or 0)
            savings_cents = total_income_cents - spent_cents
            savings_rate = (savings_cents / total_income_cents * 100.0) if total_income_cents > 0 else 0.0
            
            results.append({
                "ym": row["ym"],
                "savings_rate": savings_rate,
                "spent_cents": spent_cents,
                "income_cents": total_income_cents
            })
        
        return list(reversed(results))
