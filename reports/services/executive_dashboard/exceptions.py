"""Excepciones capa dashboard gerencial."""


class InvalidDashboardFilters(Exception):
    """Parámetros de filtro inválidos (p. ej. período invertido)."""


class LegacyReadError(Exception):
    """Error transitorio o de conexión al leer MySQL legacy."""


def is_legacy_db_error(exc: BaseException) -> bool:
    """True si la excepción proviene de una lectura MySQL legacy."""
    if isinstance(exc, LegacyReadError):
        return True
    module = getattr(type(exc), "__module__", "") or ""
    if "MySQLdb" in module or "mysql" in module.lower():
        return True
    if type(exc).__name__ in ("OperationalError", "ProgrammingError", "IntegrityError"):
        return True
    return False


def legacy_area_failure_payload(exc: Exception) -> dict:
    return {
        "disponible": False,
        "error": {"tipo": "legacy_transient_failure", "mensaje": str(exc)},
    }
