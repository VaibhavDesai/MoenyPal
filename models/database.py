"""Database connection and initialization."""
import os
import time
from sqlalchemy import create_engine, event, text
from sqlalchemy.exc import OperationalError
import streamlit as st


def _database_url() -> str:
    return os.getenv("DATABASE_URL", "sqlite:///moneypal.db")


@st.cache_resource
def get_engine():
    """Get SQLAlchemy engine with SQLite optimizations."""
    engine = create_engine(
        _database_url(),
        future=True,
        connect_args={"check_same_thread": False, "timeout": 30},
    )

    @event.listens_for(engine, "connect")
    def _set_sqlite_pragmas(dbapi_connection, connection_record):
        try:
            cursor = dbapi_connection.cursor()
            cursor.execute("PRAGMA journal_mode=WAL;")
            cursor.execute("PRAGMA synchronous=NORMAL;")
            cursor.execute("PRAGMA busy_timeout=5000;")
            cursor.close()
        except Exception:
            pass

    return engine


def with_sqlite_retry(fn, retries: int = 6, base_sleep_s: float = 0.08):
    """Retry wrapper for SQLite operations that may encounter locks."""
    last_exc: Exception | None = None
    for attempt in range(retries):
        try:
            return fn()
        except OperationalError as e:
            msg = str(e).lower()
            if "database is locked" not in msg and "database locked" not in msg:
                raise
            last_exc = e
            time.sleep(base_sleep_s * (attempt + 1))
    if last_exc:
        raise last_exc
    raise RuntimeError("SQLite retry failed")


def init_db() -> None:
    """Initialize database tables and run migrations."""
    engine = get_engine()
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
                CREATE TABLE IF NOT EXISTS tags (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL UNIQUE
                );
                """
            )
        )

        conn.execute(
            text(
                """
                CREATE TABLE IF NOT EXISTS expense_tags (
                    expense_id INTEGER NOT NULL,
                    tag_id INTEGER NOT NULL,
                    PRIMARY KEY (expense_id, tag_id),
                    FOREIGN KEY (expense_id) REFERENCES expenses(id) ON DELETE CASCADE,
                    FOREIGN KEY (tag_id) REFERENCES tags(id) ON DELETE CASCADE
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


def reset_all_data() -> None:
    """Delete all expenses, tags, and reset settings."""
    engine = get_engine()
    with engine.begin() as conn:
        conn.execute(text("DELETE FROM expense_tags;"))
        conn.execute(text("DELETE FROM tags;"))
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
