from __future__ import annotations

import re
from calendar import monthrange
from dataclasses import dataclass
from datetime import date, timedelta


# Patrón de mes: nombre completo o abreviatura común (sin ambigüedad con otros meses).
_MONTH_ALT = (
    r"enero|ene|febrero|feb|marzo|mar|abril|abr|mayo|may|junio|jun|julio|jul|agosto|ago|"
    r"septiembre|sep|setiembre|octubre|oct|noviembre|nov|diciembre|dic"
)
_MONTH_PATTERN = rf"(?P<mes>{_MONTH_ALT})"

# «entre enero 2025 y febrero 2026» / «desde enero 2025 hasta febrero 2026» (grupos m1/m2 para no repetir (?P<mes>)).
_ENTRE_NAMED_MONTHS_RANGE = re.compile(
    rf"(?:entre|de)\s+(?P<m1>{_MONTH_ALT})\s+(?:de\s+)?(?P<y1>\d{{4}})\s+(?:y|a|hasta)\s+(?P<m2>{_MONTH_ALT})\s+(?:de\s+)?(?P<y2>\d{{4}})\b",
    re.IGNORECASE,
)
_DESDE_HASTA_NAMED_MONTHS = re.compile(
    rf"desde\s+(?P<m1>{_MONTH_ALT})\s+(?:de\s+)?(?P<y1>\d{{4}})\s+hasta\s+(?P<m2>{_MONTH_ALT})\s+(?:de\s+)?(?P<y2>\d{{4}})\b",
    re.IGNORECASE,
)
# «entre enero y diciembre de 2025» (un solo año al final; debe resolverse antes que «diciembre de 2025» como mes único).
_ENTRE_MES_Y_MES_UN_ANO = re.compile(
    rf"(?:entre|de)\s+(?P<m1>{_MONTH_ALT})\s+(?:y|a)\s+(?P<m2>{_MONTH_ALT})\s+de\s+(?P<y>\d{{4}})\b",
    re.IGNORECASE,
)
_DESDE_MES_HASTA_MES_UN_ANO = re.compile(
    rf"desde\s+(?P<m1>{_MONTH_ALT})\s+hasta\s+(?P<m2>{_MONTH_ALT})\s+de\s+(?P<y>\d{{4}})\b",
    re.IGNORECASE,
)

# Año explícito: «febrero de 2025» o «febrero 2025» (muy habitual en español).
_YEAR_AFTER_MONTH = r"(?:\s+(?:de\s+)?(?P<y>\d{4}))?"

# «desde abril de 2025 a hoy», «entre abril de 2025 y hoy» (fin = fecha actual, no fin de mes).
_MONTH_TO_TODAY = re.compile(
    rf"(?:desde|entre)\s+(?:el\s+)?(?:(?P<d>\d{{1,2}})\s+de\s+)?{_MONTH_PATTERN}{_YEAR_AFTER_MONTH}\s+(?:y|a|hasta)\s+hoy\b",
    re.IGNORECASE,
)

_SINCE_MONTH_OPEN = re.compile(
    rf"desde\s+(?:el\s+)?(?:(?P<d>\d{{1,2}})\s+de\s+)?{_MONTH_PATTERN}{_YEAR_AFTER_MONTH}(?:\s|$|[,.])",
    re.IGNORECASE,
)

_MONTH_ALIASES = {
    "ene": 1,
    "enero": 1,
    "feb": 2,
    "febrero": 2,
    "mar": 3,
    "marzo": 3,
    "abr": 4,
    "abril": 4,
    "may": 5,
    "mayo": 5,
    "jun": 6,
    "junio": 6,
    "jul": 7,
    "julio": 7,
    "ago": 8,
    "agosto": 8,
    "sep": 9,
    "septiembre": 9,
    "setiembre": 9,
    "oct": 10,
    "octubre": 10,
    "nov": 11,
    "noviembre": 11,
    "dic": 12,
    "diciembre": 12,
}


def _month_number_from_token(token: str) -> int | None:
    if not token:
        return None
    return _MONTH_ALIASES.get(token.lower())


def _start_year_for_month(month: int, today: date) -> int:
    """Año de inicio cuando el usuario no indica año explícito (regla calendario vs año corrido)."""
    if month > today.month:
        return today.year - 1
    return today.year


def _build_range_from_month(
    *,
    month: int,
    day: int,
    explicit_year: int | None,
    today: date,
    range_type: str,
) -> ResolvedDateRange:
    year = explicit_year if explicit_year is not None else _start_year_for_month(month, today)
    last_dom = monthrange(year, month)[1]
    start_dom = max(1, min(day, last_dom))
    start = date(year, month, start_dom)
    end = today
    if start > end:
        # Desfase raro (datos inconsistentes); al menos no invertir el rango.
        start = end
    return ResolvedDateRange(
        start.strftime("%Y-%m-%d"),
        end.strftime("%Y-%m-%d"),
        range_type,
    )


def _try_resolve_since_month_until_today(text: str, today: date) -> ResolvedDateRange | None:
    m = _MONTH_TO_TODAY.search(text)
    if not m:
        return None
    mes_token = m.group("mes")
    month = _month_number_from_token(mes_token)
    if not month:
        return None
    explicit_year = int(m.group("y")) if m.group("y") else None
    day = int(m.group("d")) if m.group("d") else 1
    return _build_range_from_month(
        month=month,
        day=day,
        explicit_year=explicit_year,
        today=today,
        range_type="since_month_until_today",
    )


_EXPLICIT_RANGE_DDMMYYYY = re.compile(
    r"(?P<d1>\d{1,2})[-/](?P<m1>\d{1,2})[-/](?P<y1>\d{4})\s*(?:y|al|a|hasta|-|)\s*(?P<d2>\d{1,2})[-/](?P<m2>\d{1,2})[-/](?P<y2>\d{4})",
    re.IGNORECASE,
)
_EXPLICIT_RANGE_ISO = re.compile(
    r"(?P<y1>\d{4})[-/](?P<m1>\d{1,2})[-/](?P<d1>\d{1,2})\s*(?:y|al|a|hasta|-|)\s*(?P<y2>\d{4})[-/](?P<m2>\d{1,2})[-/](?P<d2>\d{1,2})",
    re.IGNORECASE,
)


def _try_explicit_calendar_range(text: str) -> ResolvedDateRange | None:
    """Rangos explícitos: DD-MM-YYYY y DD-MM-YYYY (o con /), o ISO YYYY-MM-DD."""
    m = _EXPLICIT_RANGE_DDMMYYYY.search(text)
    if m:
        try:
            d1, mo1, y1 = int(m.group("d1")), int(m.group("m1")), int(m.group("y1"))
            d2, mo2, y2 = int(m.group("d2")), int(m.group("m2")), int(m.group("y2"))
            start = date(y1, mo1, d1)
            end = date(y2, mo2, d2)
        except ValueError:
            return None
        if start > end:
            start, end = end, start
        return ResolvedDateRange(
            start.strftime("%Y-%m-%d"),
            end.strftime("%Y-%m-%d"),
            "explicit_calendar_range",
        )
    m = _EXPLICIT_RANGE_ISO.search(text)
    if m:
        try:
            y1, mo1, d1 = int(m.group("y1")), int(m.group("m1")), int(m.group("d1"))
            y2, mo2, d2 = int(m.group("y2")), int(m.group("m2")), int(m.group("d2"))
            start = date(y1, mo1, d1)
            end = date(y2, mo2, d2)
        except ValueError:
            return None
        if start > end:
            start, end = end, start
        return ResolvedDateRange(
            start.strftime("%Y-%m-%d"),
            end.strftime("%Y-%m-%d"),
            "explicit_calendar_range",
        )
    return None


def _try_resolve_nominal_month_implicit_current_year(text: str, today: date) -> ResolvedDateRange | None:
    """
    Mes calendario completo sin año explícito: «en abril», «mes de marzo», «durante febrero».
    Se usa el **año calendario actual** (`today.year`). No aplica si junto al mes hay un año de 4 dígitos
    (eso lo cubre `_try_resolve_named_calendar_month_with_year`).
    """
    t = (text or "").lower()
    if re.search(rf"\b{_MONTH_PATTERN}\s+(?:de\s+)?\d{{4}}\b", t, re.IGNORECASE):
        return None
    patterns = [
        re.compile(rf"(?:^|[\s,])(?:en|durante)\s+(?P<mes>{_MONTH_ALT})\b", re.IGNORECASE),
        re.compile(rf"(?:^|[\s])(?:el\s+)?mes\s+de\s+(?P<mes>{_MONTH_ALT})\b", re.IGNORECASE),
        re.compile(rf"(?:^|[\s])del\s+mes\s+de\s+(?P<mes>{_MONTH_ALT})\b", re.IGNORECASE),
    ]
    for rx in patterns:
        m = rx.search(t)
        if not m:
            continue
        mes_token = m.group("mes")
        month = _month_number_from_token(mes_token)
        if not month:
            continue
        year = today.year
        last_dom = monthrange(year, month)[1]
        return ResolvedDateRange(
            date(year, month, 1).strftime("%Y-%m-%d"),
            date(year, month, last_dom).strftime("%Y-%m-%d"),
            "calendar_month_named_implicit_year",
        )
    return None


def _try_resolve_named_calendar_month_with_year(text: str) -> ResolvedDateRange | None:
    """
    Mes calendario completo cuando el usuario indica mes nominal + año explícito, p. ej.
    «febrero 2026», «mes de febrero de 2026», «en el mes de febrero 2026».

    No aplica a rangos «desde …» ya cubiertos por otras ramas (se resuelven antes en resolve_from_text).
    """
    _MES_ANO = re.compile(
        rf"(?:\b(?:el\s+)?mes\s+de\s+|\ben\s+(?:el\s+)?|\ben\s+el\s+mes\s+de\s+)?\b{_MONTH_PATTERN}\s*(?:de\s+)?(?P<y>\d{{4}})\b",
        re.IGNORECASE,
    )
    m = _MES_ANO.search(text)
    if not m:
        return None
    mes_token = m.group("mes")
    month = _month_number_from_token(mes_token)
    if not month:
        return None
    try:
        year = int(m.group("y"))
    except (TypeError, ValueError):
        return None
    last_dom = monthrange(year, month)[1]
    return ResolvedDateRange(
        date(year, month, 1).strftime("%Y-%m-%d"),
        date(year, month, last_dom).strftime("%Y-%m-%d"),
        "calendar_month_named_year",
    )


def _try_resolve_between_named_months(text: str) -> ResolvedDateRange | None:
    """
    Rango entre dos meses nominales con año: «entre enero 2025 y febrero 2026»,
    «de marzo 2025 a junio 2025», «desde enero 2025 hasta febrero 2026».
    """
    for rx in (_ENTRE_NAMED_MONTHS_RANGE, _DESDE_HASTA_NAMED_MONTHS):
        m = rx.search(text)
        if not m:
            continue
        mo1 = _month_number_from_token(m.group("m1"))
        mo2 = _month_number_from_token(m.group("m2"))
        if not mo1 or not mo2:
            continue
        try:
            y1 = int(m.group("y1"))
            y2 = int(m.group("y2"))
        except (TypeError, ValueError):
            continue
        d_a = date(y1, mo1, 1)
        d_b = date(y2, mo2, monthrange(y2, mo2)[1])
        if d_a <= d_b:
            start, end = d_a, d_b
        else:
            start = date(y2, mo2, 1)
            end = date(y1, mo1, monthrange(y1, mo1)[1])
        return ResolvedDateRange(
            start.strftime("%Y-%m-%d"),
            end.strftime("%Y-%m-%d"),
            "calendar_month_range_named",
        )
    return None


def _try_resolve_entre_meses_mismo_anio_explicito(text: str) -> ResolvedDateRange | None:
    """
    «entre enero y diciembre de 2025», «de marzo a junio de 2024»,
    «desde enero hasta diciembre de 2025» (mismo año para ambos meses).
    """
    for rx in (_ENTRE_MES_Y_MES_UN_ANO, _DESDE_MES_HASTA_MES_UN_ANO):
        m = rx.search(text)
        if not m:
            continue
        mo1 = _month_number_from_token(m.group("m1"))
        mo2 = _month_number_from_token(m.group("m2"))
        if not mo1 or not mo2:
            continue
        try:
            year = int(m.group("y"))
        except (TypeError, ValueError):
            continue
        d_a = date(year, mo1, 1)
        d_b = date(year, mo2, monthrange(year, mo2)[1])
        if d_a <= d_b:
            start, end = d_a, d_b
        else:
            start = date(year, mo2, 1)
            end = date(year, mo1, monthrange(year, mo1)[1])
        return ResolvedDateRange(
            start.strftime("%Y-%m-%d"),
            end.strftime("%Y-%m-%d"),
            "calendar_month_range_same_year",
        )
    return None


def _try_resolve_since_month_open_ended(text: str, today: date) -> ResolvedDateRange | None:
    """`desde febrero` sin `a hoy`: se asume fin en la fecha actual (uso frecuente en consultas de negocio)."""
    if _MONTH_TO_TODAY.search(text):
        return None
    m = _SINCE_MONTH_OPEN.search(text)
    if not m:
        return None
    tail = text[m.end() :].lstrip()
    if tail.startswith("a ") and not tail.startswith("a hoy"):
        return None
    if tail.startswith("hasta ") and not tail.startswith("hasta hoy"):
        return None
    mes_token = m.group("mes")
    month = _month_number_from_token(mes_token)
    if not month:
        return None
    explicit_year = int(m.group("y")) if m.group("y") else None
    day = int(m.group("d")) if m.group("d") else 1
    return _build_range_from_month(
        month=month,
        day=day,
        explicit_year=explicit_year,
        today=today,
        range_type="since_month_open_ended",
    )


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
    def try_parse_explicit_range(message_text: str) -> ResolvedDateRange | None:
        """Detecta rangos DD/MM/YYYY o ISO en el texto (sin exigir que sea el único contenido)."""
        return _try_explicit_calendar_range((message_text or "").lower())

    @staticmethod
    def resolve_from_text(message_text: str, *, require_period: bool = False) -> ResolvedDateRange:
        text = (message_text or "").lower()
        today = date.today()

        since_until = _try_resolve_since_month_until_today(text, today)
        if since_until:
            return since_until

        since_open = _try_resolve_since_month_open_ended(text, today)
        if since_open:
            return since_open

        explicit = _try_explicit_calendar_range(text)
        if explicit:
            return explicit

        entre_meses = _try_resolve_between_named_months(text)
        if entre_meses:
            return entre_meses

        entre_mismo_anio = _try_resolve_entre_meses_mismo_anio_explicito(text)
        if entre_mismo_anio:
            return entre_mismo_anio

        named_month_year = _try_resolve_named_calendar_month_with_year(text)
        if named_month_year:
            return named_month_year

        nominal_implicit = _try_resolve_nominal_month_implicit_current_year(text, today)
        if nominal_implicit:
            return nominal_implicit

        if "hoy" in text and "desde" not in text:
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
