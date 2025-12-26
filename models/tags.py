"""Tag management models."""
from sqlalchemy import text
from .database import get_engine, with_sqlite_retry


def normalize_tags(values: list[str] | None) -> list[str]:
    """Normalize and deduplicate tags."""
    if not values:
        return []
    out: list[str] = []
    seen: set[str] = set()
    for v in values:
        name = (v or "").strip()
        if not name:
            continue
        key = name.casefold()
        if key in seen:
            continue
        seen.add(key)
        out.append(name)
    return out


def list_all_tags(limit: int = 500) -> list[str]:
    """Get all tags from database."""
    engine = get_engine()
    with engine.begin() as conn:
        rows = conn.execute(
            text(
                """
                SELECT name
                FROM tags
                ORDER BY LOWER(name) ASC
                LIMIT :limit;
                """
            ),
            {"limit": int(limit)},
        ).mappings().all()
        return [str(r.get("name") or "") for r in rows if (r.get("name") or "").strip()]


def get_or_create_tag_ids(conn, names: list[str]) -> list[int]:
    """Get or create tag IDs for given tag names."""
    names = normalize_tags(names)
    if not names:
        return []

    def _op():
        for n in names:
            conn.execute(
                text("INSERT OR IGNORE INTO tags (name) VALUES (:name);"),
                {"name": n},
            )

        rows = conn.execute(
            text(
                """
                SELECT id
                FROM tags
                WHERE name IN ({placeholders});
                """.format(placeholders=", ".join([f":n{i}" for i in range(len(names))]))
            ),
            {f"n{i}": names[i] for i in range(len(names))},
        ).mappings().all()
        return [int(r["id"]) for r in rows]

    return with_sqlite_retry(_op)


def set_expense_tags(conn, *, expense_id: int, tags: list[str]) -> None:
    """Set tags for an expense."""
    tags = normalize_tags(tags)

    def _op():
        conn.execute(text("DELETE FROM expense_tags WHERE expense_id = :id;"), {"id": int(expense_id)})
        if not tags:
            return
        tag_ids = get_or_create_tag_ids(conn, tags)
        for tid in tag_ids:
            conn.execute(
                text(
                    """
                    INSERT OR IGNORE INTO expense_tags (expense_id, tag_id)
                    VALUES (:expense_id, :tag_id);
                    """
                ),
                {"expense_id": int(expense_id), "tag_id": int(tid)},
            )

    with_sqlite_retry(_op)
