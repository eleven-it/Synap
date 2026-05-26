"""Excepciones capa dashboard gerencial."""


class InvalidDashboardFilters(Exception):
    """Parámetros de filtro inválidos (p. ej. período invertido)."""


class LegacyReadError(Exception):
    """Error transitorio o de conexión al leer MySQL legacy."""
