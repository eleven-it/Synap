"""
Lectura de parámetros ``configuracion_ecom`` (MySQL legacy por base_empresa).

Usado para elegir fuente de relación vendedor-cliente / vendedor-marca
(legacy vs tablas ``vendedores_*_asignacion``).
"""

from __future__ import annotations

from typing import Literal, Optional

from core.mysql_pool import get_mysql_pool

FuenteVendedorAsignacion = Literal["legacy", "tabla"]

_KEYS_FUENTE = {
    "cliente": "ecom_fuente_vendedor_cliente",
    "marca": "ecom_fuente_vendedor_marca",
}


def _normalizar_fuente(valor: Optional[str]) -> FuenteVendedorAsignacion:
    v = (valor or "").strip().lower()
    if v == "tabla":
        return "tabla"
    return "legacy"


def leer_valor_configuracion_ecom(base_empresa: str, key_permiso: str, default: str = "") -> str:
    """Devuelve ``valor_permiso`` o ``default`` si no existe la fila."""
    key = (key_permiso or "").strip()
    if not key:
        return default
    pool = get_mysql_pool()
    sql = """
        SELECT valor_permiso
        FROM configuracion_ecom
        WHERE key_permiso = %s
        LIMIT 1
    """
    with pool.get_connection(base_empresa) as conn:
        cursor = conn.cursor()
        try:
            cursor.execute(sql, (key,))
            row = cursor.fetchone()
        finally:
            cursor.close()
    if not row:
        return default
    if isinstance(row, dict):
        raw = row.get("valor_permiso")
    else:
        raw = row[0]
    return str(raw).strip() if raw is not None else default


def fuente_vendedor_asignacion(
    base_empresa: str,
    entidad: Literal["cliente", "marca"],
    *,
    sesion_valor: Optional[str] = None,
) -> FuenteVendedorAsignacion:
    """
    Resuelve ``legacy`` | ``tabla``.

  ``sesion_valor``: si la sesión Synap ya trae el flag (paridad PHP ``$_SESSION``), se usa primero.
    """
    if sesion_valor is not None:
        return _normalizar_fuente(sesion_valor)
    key = _KEYS_FUENTE.get(entidad)
    if not key:
        return "legacy"
    return _normalizar_fuente(leer_valor_configuracion_ecom(base_empresa, key, "legacy"))
