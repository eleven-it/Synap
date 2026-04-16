from __future__ import annotations

from calendar import monthrange
from dataclasses import dataclass
from datetime import date, timedelta


@dataclass
class ResolvedDateRange:
    start_date: str | None
    end_date: str | None
    range_type: str
    requires_clarification: bool = False
    clarification_question: str | None = None


class DateRangeService:
    """Resolución determinística de rangos temporales básicos en español."""

    @staticmethod
    def resolve_from_text(message_text: str, *, require_period: bool = False) -> ResolvedDateRange:
        text = (message_text or "").lower()
        today = date.today()

        if "hoy" in text:
            value = today.strftime("%Y-%m-%d")
            return ResolvedDateRange(value, value, "calendar_day")

        if "ayer" in text:
            target = today - timedelta(days=1)
            value = target.strftime("%Y-%m-%d")
            return ResolvedDateRange(value, value, "calendar_day")

        if "últimos 7 días" in text or "ultimos 7 dias" in text:
            start = today - timedelta(days=6)
            return ResolvedDateRange(start.strftime("%Y-%m-%d"), today.strftime("%Y-%m-%d"), "rolling_7_days")

        if "últimos 30 días" in text or "ultimos 30 dias" in text:
            start = today - timedelta(days=29)
            return ResolvedDateRange(start.strftime("%Y-%m-%d"), today.strftime("%Y-%m-%d"), "rolling_30_days")

        if "mes pasado" in text:
            year = today.year
            month = today.month - 1
            if month == 0:
                month = 12
                year -= 1
            end_day = monthrange(year, month)[1]
            return ResolvedDateRange(
                date(year, month, 1).strftime("%Y-%m-%d"),
                date(year, month, end_day).strftime("%Y-%m-%d"),
                "calendar_month_previous",
            )

        if "este mes" in text or "mes actual" in text:
            end_day = monthrange(today.year, today.month)[1]
            return ResolvedDateRange(
                date(today.year, today.month, 1).strftime("%Y-%m-%d"),
                date(today.year, today.month, end_day).strftime("%Y-%m-%d"),
                "calendar_month_current",
            )

        if "trimestre actual" in text or "este trimestre" in text:
            quarter = ((today.month - 1) // 3) + 1
            start_month = (quarter - 1) * 3 + 1
            end_month = start_month + 2
            end_day = monthrange(today.year, end_month)[1]
            return ResolvedDateRange(
                date(today.year, start_month, 1).strftime("%Y-%m-%d"),
                date(today.year, end_month, end_day).strftime("%Y-%m-%d"),
                "calendar_quarter_current",
            )

        if "este año" in text or "año actual" in text or "ano actual" in text:
            return ResolvedDateRange(
                date(today.year, 1, 1).strftime("%Y-%m-%d"),
                date(today.year, 12, 31).strftime("%Y-%m-%d"),
                "calendar_year_current",
            )

        if require_period:
            return ResolvedDateRange(
                None,
                None,
                "unknown",
                requires_clarification=True,
                clarification_question="¿Sobre qué período querés hacer la consulta?",
            )

        return ResolvedDateRange(None, None, "unspecified")

    @staticmethod
    def previous_equivalent(range_type: str, start_date_str: str, end_date_str: str) -> ResolvedDateRange | None:
        if not start_date_str or not end_date_str:
            return None
        start = date.fromisoformat(start_date_str)
        end = date.fromisoformat(end_date_str)

        if range_type == "calendar_month_current":
            prev_month_last_day = start - timedelta(days=1)
            prev_year = prev_month_last_day.year
            prev_month = prev_month_last_day.month
            end_day = monthrange(prev_year, prev_month)[1]
            return ResolvedDateRange(
                date(prev_year, prev_month, 1).strftime("%Y-%m-%d"),
                date(prev_year, prev_month, end_day).strftime("%Y-%m-%d"),
                "calendar_month_previous",
            )

        delta_days = (end - start).days
        prev_end = start - timedelta(days=1)
        prev_start = prev_end - timedelta(days=delta_days)
        return ResolvedDateRange(
            prev_start.strftime("%Y-%m-%d"),
            prev_end.strftime("%Y-%m-%d"),
            f"previous_{range_type}",
        )
