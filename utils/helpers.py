"""Helper utility functions."""
import datetime as dt
from .constants import CATEGORY_LABELS


def category_label(cat: str) -> str:
    """Get display label for category."""
    c = (cat or "").strip()
    return CATEGORY_LABELS.get(c, c or "Misc")


def parse_occurred_at(value: str) -> dt.datetime:
    """Parse occurred_at timestamp."""
    try:
        return dt.datetime.fromisoformat(value)
    except Exception:
        try:
            return dt.datetime.strptime(value, "%Y-%m-%d %H:%M:%S")
        except Exception:
            return dt.datetime(1970, 1, 1)


def format_ym(ym: str) -> str:
    """Format year-month string."""
    try:
        y, m = ym.split("-")
        return dt.date(int(y), int(m), 1).strftime("%b %Y")
    except Exception:
        return ym


def format_yw(yw: str) -> str:
    """Format year-week string."""
    try:
        y, w = yw.split("-W")
        return f"{y} W{int(w):02d}"
    except Exception:
        return yw
