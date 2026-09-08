"""Synthetic fixtures for the fictional DEMO company. Never market observations."""
from datetime import datetime, timedelta, timezone
import math


def prices() -> dict:
    days = []
    day = datetime(2025, 1, 1, tzinfo=timezone.utc)
    while len(days) < 120:
        if day.weekday() < 5:
            days.append(int(day.timestamp()))
        day += timedelta(days=1)
    closes = [round(74 + i * .19 + 2.8 * math.sin(i / 7), 2) for i in range(120)]
    return {
        "ticker": "DEMO", "timestamps": days, "closes": closes,
        "opens": [round(c - .4, 2) for c in closes],
        "highs": [round(c + 1.2, 2) for c in closes],
        "lows": [round(c - 1.3, 2) for c in closes],
        "volumes": [1_000_000 + int(120_000 * math.sin(i / 4)) for i in range(120)],
    }


def fundamentals() -> dict:
    return {
        "ticker": "DEMO", "company_name": "Demo Software Co.",
        "profile": {"name": "Demo Software Co.", "sicDescription": "Fictional subscription software business"},
        "period_end": "2025-12-31", "filed": "2026-02-20",
        "operating_cash_flow": 8_000_000_000.0, "capex": 2_000_000_000.0,
        "shares": 600_000_000.0, "debt": 2_000_000_000.0,
        "current_price": 96.0, "price_as_of": "2026-02-23",
        "sources": [], "warnings": ["All company figures and narratives are synthetic demo fixtures."],
    }
