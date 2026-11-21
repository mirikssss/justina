"""Панель рисков Минюста: обезличенные агрегаты по тревогам. Личных данных, номеров документов и идентификаторов граждан нет.

Что видно: сколько тревог по правилам и важности, доля ответов «Это не я», динамика по дням, скорость доставки тревог.
Чего нет и что нужно для настоящей панели: разрез по регионам и нотариусам (нет в данных прототипа), порог
k-анонимности для малых групп (на малых объёмах прототипа не применяется).
"""

from datetime import UTC, datetime
from typing import Any

from storozh.shared import db


async def risk_stats(days: int = 30) -> dict[str, Any]:
    days = max(1, min(days, 365))
    async with db.connect("guard") as conn:
        by_rule = await (await conn.execute(
            """SELECT rule_id, severity, count(*)::int AS n,
                      count(*) FILTER (WHERE verdict = 'not_me')::int AS not_me,
                      count(*) FILTER (WHERE verdict = 'me')::int AS me
               FROM alerts WHERE created_at > now() - make_interval(days => %s)
               GROUP BY rule_id, severity ORDER BY n DESC""", (days,))).fetchall()
        per_day = await (await conn.execute(
            """SELECT to_char(created_at::date, 'YYYY-MM-DD') AS day, count(*)::int AS n,
                      count(*) FILTER (WHERE severity = 'critical')::int AS critical
               FROM alerts WHERE created_at > now() - make_interval(days => %s)
               GROUP BY 1 ORDER BY 1""", (days,))).fetchall()
        lat = await (await conn.execute(
            """SELECT count(*)::int AS n,
                      percentile_cont(0.5) WITHIN GROUP (ORDER BY extract(epoch FROM sent_at - detected_at)) AS p50,
                      percentile_cont(0.95) WITHIN GROUP (ORDER BY extract(epoch FROM sent_at - detected_at)) AS p95
               FROM alerts WHERE sent_at IS NOT NULL AND detected_at IS NOT NULL
                 AND created_at > now() - make_interval(days => %s)""", (days,))).fetchone()
    total = sum(r["n"] for r in by_rule)
    answered = sum(r["me"] + r["not_me"] for r in by_rule)
    not_me = sum(r["not_me"] for r in by_rule)
    return {
        "days": days, "alerts": total, "answered": answered, "not_me": not_me,
        "not_me_share": round(not_me / answered, 3) if answered else None,
        "by_rule": [{"rule_id": r["rule_id"], "severity": r["severity"], "count": r["n"],
                     "not_me": r["not_me"], "me": r["me"]} for r in by_rule],
        "per_day": [{"day": r["day"], "count": r["n"], "critical": r["critical"]} for r in per_day],
        "delivery_seconds": {"measured": lat["n"], "p50": round(lat["p50"], 2) if lat["p50"] is not None else None,
                             "p95": round(lat["p95"], 2) if lat["p95"] is not None else None},
        "generated_at": datetime.now(UTC).isoformat(timespec="seconds"),
    }
