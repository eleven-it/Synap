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

KEY_VALIDAR_STOCK_PEDIDOS = "ecom_validar_stock_pedidos"


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


def _normalizar_si_no(valor: Optional[str]) -> bool:
    """True si el valor representa «Sí» (validar stock); False para no|0|false|off|n."""
    v = (valor or "").strip().lower()
    if v in ("no", "0", "false", "off", "n"):
        return False
    return True


def pedidos_validan_stock(base_empresa: str) -> bool:
    """
    Lee ``ecom_validar_stock_pedidos`` en ``configuracion_ecom``.

    Default **Si** si falta la fila (comportamiento legacy).
    """
    raw = leer_valor_configuracion_ecom(
        base_empresa, KEY_VALIDAR_STOCK_PEDIDOS, "Si"
    )
    return _normalizar_si_no(raw)


def _meta_fila_config(key: str) -> dict:
    """Metadatos de fila para INSERT (respetar anchos típicos del schema legacy)."""
    nombres = {
        KEY_VALIDAR_STOCK_PEDIDOS: "Validar stock en pedidos",
    }
    detalles = {
        KEY_VALIDAR_STOCK_PEDIDOS: (
            "Si: bloquea PED sin disponible. No: permite PED sin stock (p.ej. fabricación MPR)."
        ),
    }
    return {
        "nombre": (nombres.get(key) or key)[:100],
        "detalle": (detalles.get(key) or "")[:1000],
        # grupo_permiso es VARCHAR(20) en schema típico
        "grupo": "Ecom Ventas"[:20],
        "tipo": "Si/No"[:20],
        "detalle_valor": "Si-No"[:200],
    }


def escribir_valor_configuracion_ecom(
    base_empresa: str, key_permiso: str, valor: str
) -> bool:
    """UPDATE si existe la fila; INSERT mínimo si no. Escribe en ``configuracion_ecom``."""
    key = (key_permiso or "").strip()
    if not key or not (base_empresa or "").strip():
        return False
    val = str(valor or "").strip()[:200]
    meta = _meta_fila_config(key)
    pool = get_mysql_pool()
    with pool.get_connection(base_empresa) as conn:
        cursor = conn.cursor()
        try:
            cursor.execute(
                """
                SELECT 1 FROM configuracion_ecom WHERE key_permiso = %s LIMIT 1
                """,
                (key,),
            )
            existe = cursor.fetchone() is not None
            if existe:
                cursor.execute(
                    """
                    UPDATE configuracion_ecom
                    SET valor_permiso = %s
                    WHERE key_permiso = %s
                    """,
                    (val, key),
                )
            else:
                cursor.execute(
                    """
                    INSERT INTO configuracion_ecom (
                        key_permiso, nombre_permiso, detalle_permiso,
                        grupo_permiso, tipo_permiso, valor_permiso, detalle_valor_permiso
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s)
                    """,
                    (
                        key[:60],
                        meta["nombre"],
                        meta["detalle"],
                        meta["grupo"],
                        meta["tipo"],
                        val,
                        meta["detalle_valor"],
                    ),
                )
            conn.commit()
            return True
        except Exception:
            try:
                conn.rollback()
            except Exception:
                pass
            raise
        finally:
            cursor.close()
