"""Settings management models."""
from sqlalchemy import text
from .database import get_engine


def get_settings() -> dict:
    """Get application settings."""
    engine = get_engine()
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
    """Save application settings."""
    engine = get_engine()
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
