"""Expense management models."""
import datetime as dt
from sqlalchemy import text
from .database import get_engine
from .tags import set_expense_tags


def insert_expense(*, item_name: str, amount: float, category: str, occurred_on: dt.date, tags: list[str] | None = None) -> None:
    """Insert a new expense."""
    engine = get_engine()
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
        expense_id = int(conn.execute(text("SELECT last_insert_rowid() AS id;")).mappings().first()["id"])
        set_expense_tags(conn, expense_id=expense_id, tags=list(tags or []))


def get_expense(expense_id: int) -> dict | None:
    """Get expense by ID with tags."""
    engine = get_engine()
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
        if not row:
            return None

        tags_rows = conn.execute(
            text(
                """
                SELECT t.name AS name
                FROM expense_tags et
                JOIN tags t ON t.id = et.tag_id
                WHERE et.expense_id = :id
                ORDER BY LOWER(t.name) ASC;
                """
            ),
            {"id": int(expense_id)},
        ).mappings().all()
        d = dict(row)
        d["tags"] = [str(r.get("name") or "") for r in tags_rows if (r.get("name") or "").strip()]
        return d


def update_expense(
    *,
    expense_id: int,
    item_name: str,
    amount: float,
    category: str,
    occurred_on: dt.date,
    tags: list[str] | None = None,
) -> None:
    """Update an existing expense."""
    engine = get_engine()
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
        set_expense_tags(conn, expense_id=int(expense_id), tags=list(tags or []))


def delete_expense(expense_id: int) -> None:
    """Delete an expense."""
    engine = get_engine()
    with engine.begin() as conn:
        conn.execute(text("DELETE FROM expenses WHERE id = :id;"), {"id": int(expense_id)})


def list_transactions(
    *,
    search: str = "",
    limit: int = 500,
    start_date: dt.date | None = None,
    end_date: dt.date | None = None,
    tag: str | None = None,
):
    """List transactions with optional filters."""
    engine = get_engine()
    q = (search or "").strip().lower()
    tag_value = (tag or "").strip()

    where_parts: list[str] = []
    params: dict = {"limit": int(limit)}

    if q:
        where_parts.append(
            "(LOWER(COALESCE(e.note, '')) LIKE :q OR LOWER(COALESCE(e.category, '')) LIKE :q OR LOWER(COALESCE(t.name, '')) LIKE :q)"
        )
        params["q"] = f"%{q}%"

    if start_date is not None:
        params["start"] = dt.datetime.combine(start_date, dt.time(0, 0, 0)).isoformat()
        where_parts.append("e.occurred_at >= :start")

    if end_date is not None:
        end_excl = dt.datetime.combine(end_date + dt.timedelta(days=1), dt.time(0, 0, 0)).isoformat()
        params["end"] = end_excl
        where_parts.append("e.occurred_at < :end")

    if tag_value:
        where_parts.append("LOWER(t.name) = LOWER(:tag)")
        params["tag"] = tag_value

    where_sql = "" if not where_parts else ("WHERE " + " AND ".join(where_parts))

    sql = f"""
        SELECT e.id,
               e.occurred_at,
               e.note,
               e.category,
               e.amount_cents,
               COALESCE(GROUP_CONCAT(t.name, ', '), '') AS tags
        FROM expenses e
        LEFT JOIN expense_tags et ON et.expense_id = e.id
        LEFT JOIN tags t ON t.id = et.tag_id
        {where_sql}
        GROUP BY e.id
        ORDER BY e.occurred_at DESC, e.id DESC
        LIMIT :limit;
    """

    with engine.begin() as conn:
        rows = conn.execute(text(sql), params).mappings()
        return list(rows)


def spent_by_category_for_month(today: dt.date) -> dict:
    """Get spending by category for current month."""
    engine = get_engine()
    start = dt.datetime(today.year, today.month, 1).isoformat()
    if today.month == 12:
        end = dt.datetime(today.year + 1, 1, 1).isoformat()
    else:
        end = dt.datetime(today.year, today.month + 1, 1).isoformat()

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
        
        from utils.constants import CATEGORIES
        result = {c: 0 for c in CATEGORIES}
        for r in rows:
            cat = r["category"]
            if cat in result:
                result[cat] = int(r["spent_cents"] or 0)
        return result


def spent_total_for_month(today: dt.date) -> int:
    """Get total spending for current month."""
    engine = get_engine()
    start = dt.datetime(today.year, today.month, 1).isoformat()
    if today.month == 12:
        end = dt.datetime(today.year + 1, 1, 1).isoformat()
    else:
        end = dt.datetime(today.year, today.month + 1, 1).isoformat()

    with engine.begin() as conn:
        v = conn.execute(
            text(
                """
                SELECT COALESCE(SUM(amount_cents), 0) AS total_cents
                FROM expenses
                WHERE occurred_at >= :start AND occurred_at < :end;
                """
            ),
            {"start": start, "end": end},
        ).mappings().first()
        return int(v["total_cents"] or 0) if v else 0
