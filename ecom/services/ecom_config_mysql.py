"""
Lectura de parámetros ``configuracion_ecom`` (MySQL legacy por base_empresa).

Usado para elegir fuente de relación vendedor-cliente / vendedor-marca
(legacy vs tablas ``vendedores_*_asignacion``).
"""

from __future__ import annotations

from decimal import Decimal, InvalidOperation
from typing import Any, Dict, Literal, Optional

from core.mysql_pool import get_mysql_pool

FuenteVendedorAsignacion = Literal["legacy", "tabla"]

_KEYS_FUENTE = {
    "cliente": "ecom_fuente_vendedor_cliente",
    "marca": "ecom_fuente_vendedor_marca",
}

KEY_VALIDAR_STOCK_PEDIDOS = "ecom_validar_stock_pedidos"
KEY_WORKFLOW_JERARQUIA_COMERCIAL = "ecom_workflow_jerarquia_comercial"
KEY_APROBACION_PEDIDOS_ACTIVA = "ecom_aprobacion_pedidos_activa"
KEY_APROBACION_UMBRAL_MONTO = "ecom_aprobacion_umbral_monto"
KEY_APROBACION_UMBRAL_DESC_PIE = "ecom_aprobacion_umbral_desc_pie"
KEY_APROBACION_UMBRAL_DESC_RENGLON = "ecom_aprobacion_umbral_desc_renglon"
KEY_OBJETIVOS_EN_PEDIDOS = "ecom_objetivos_en_pedidos"
KEY_BACKORDER_EN_PEDIDOS = "ecom_backorder_en_pedidos"

_WORKFLOW_UMBRAL_KEYS = (
    KEY_APROBACION_UMBRAL_MONTO,
    KEY_APROBACION_UMBRAL_DESC_PIE,
    KEY_APROBACION_UMBRAL_DESC_RENGLON,
)


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


def workflow_jerarquia_comercial_activo(base_empresa: str) -> bool:
    """
    Master flag ``ecom_workflow_jerarquia_comercial`` (default No).

    Cuando está inactivo, los flujos MUST usar carteras JSON legacy.
    """
    raw = leer_valor_configuracion_ecom(
        base_empresa, KEY_WORKFLOW_JERARQUIA_COMERCIAL, "No"
    )
    return _normalizar_si_no(raw)


def aprobacion_pedidos_activa(base_empresa: str) -> bool:
    """
    Subflag ``ecom_aprobacion_pedidos_activa`` (default No).

    Si el master workflow está inactivo, MUST devolver False aunque la fila diga Sí.
    """
    if not workflow_jerarquia_comercial_activo(base_empresa):
        return False
    raw = leer_valor_configuracion_ecom(
        base_empresa, KEY_APROBACION_PEDIDOS_ACTIVA, "No"
    )
    return _normalizar_si_no(raw)


def objetivos_en_pedidos_activo(base_empresa: str) -> bool:
    """Atajo hub: mostrar enlace a objetivos desde pedidos (default No)."""
    raw = leer_valor_configuracion_ecom(
        base_empresa, KEY_OBJETIVOS_EN_PEDIDOS, "No"
    )
    return _normalizar_si_no(raw)


def backorder_en_pedidos_activo(base_empresa: str) -> bool:
    """Atajo hub: habilitar flujo backorder desde pedidos (default No)."""
    raw = leer_valor_configuracion_ecom(
        base_empresa, KEY_BACKORDER_EN_PEDIDOS, "No"
    )
    return _normalizar_si_no(raw)


def _leer_umbral_aprobacion(
    base_empresa: str, key: str
) -> Optional[Decimal]:
    """
    Lee umbral numérico; vacío o inválido → None (regla inactiva, REQ-APR-02 default).
    """
    raw = leer_valor_configuracion_ecom(base_empresa, key, "")
    txt = (raw or "").strip()
    if not txt or txt in ("-", "0"):
        return None
    try:
        val = Decimal(txt.replace(",", "."))
        if val <= 0:
            return None
        return val
    except (InvalidOperation, ValueError):
        return None


def umbrales_aprobacion_pedidos(base_empresa: str) -> Dict[str, Optional[Decimal]]:
    """Umbrales comerciales para el motor de aprobación (Fase 4)."""
    return {
        "monto": _leer_umbral_aprobacion(base_empresa, KEY_APROBACION_UMBRAL_MONTO),
        "desc_pie": _leer_umbral_aprobacion(
            base_empresa, KEY_APROBACION_UMBRAL_DESC_PIE
        ),
        "desc_renglon": _leer_umbral_aprobacion(
            base_empresa, KEY_APROBACION_UMBRAL_DESC_RENGLON
        ),
    }


def leer_config_workflow_comercial(base_empresa: str) -> Dict[str, Any]:
    """Snapshot para bootstrap/API de ajustes workflow."""
    master = workflow_jerarquia_comercial_activo(base_empresa)
    umbrales = umbrales_aprobacion_pedidos(base_empresa)
    return {
        "workflow_jerarquia_comercial": master,
        "aprobacion_pedidos_activa": aprobacion_pedidos_activa(base_empresa),
        "aprobacion_pedidos_activa_raw": _normalizar_si_no(
            leer_valor_configuracion_ecom(
                base_empresa, KEY_APROBACION_PEDIDOS_ACTIVA, "No"
            )
        ),
        "objetivos_en_pedidos": objetivos_en_pedidos_activo(base_empresa),
        "backorder_en_pedidos": backorder_en_pedidos_activo(base_empresa),
        "umbral_monto": _decimal_a_str(umbrales["monto"]),
        "umbral_desc_pie": _decimal_a_str(umbrales["desc_pie"]),
        "umbral_desc_renglon": _decimal_a_str(umbrales["desc_renglon"]),
    }


def _decimal_a_str(val: Optional[Decimal]) -> str:
    if val is None:
        return ""
    s = format(val, "f")
    if "." in s:
        s = s.rstrip("0").rstrip(".")
    return s


def _normalizar_umbral_texto(raw: Any) -> str:
    """Normaliza umbral para persistencia; vacío = regla inactiva."""
    if raw is None:
        return ""
    txt = str(raw).strip().replace(",", ".")
    if not txt or txt in ("-", "0", "0.0"):
        return ""
    try:
        val = Decimal(txt)
        if val <= 0:
            return ""
        s = format(val, "f")
        if "." in s:
            s = s.rstrip("0").rstrip(".")
        return s
    except (InvalidOperation, ValueError):
        return ""


def _bool_a_si_no(raw: Any) -> str:
    if raw in (True, "true", "True", 1, "1", "Si", "si", "Sí", "sí"):
        return "Si"
    return "No"


def guardar_config_workflow_comercial(
    base_empresa: str, payload: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Persiste flags y umbrales de workflow comercial.

    Devuelve snapshot actualizado (``aprobacion_pedidos_activa`` respeta master OFF).
    """
    escribir_valor_configuracion_ecom(
        base_empresa,
        KEY_WORKFLOW_JERARQUIA_COMERCIAL,
        _bool_a_si_no(payload.get("workflow_jerarquia_comercial")),
    )
    if "aprobacion_pedidos_activa" in payload:
        escribir_valor_configuracion_ecom(
            base_empresa,
            KEY_APROBACION_PEDIDOS_ACTIVA,
            _bool_a_si_no(payload.get("aprobacion_pedidos_activa")),
        )
    if "objetivos_en_pedidos" in payload:
        escribir_valor_configuracion_ecom(
            base_empresa,
            KEY_OBJETIVOS_EN_PEDIDOS,
            _bool_a_si_no(payload.get("objetivos_en_pedidos")),
        )
    if "backorder_en_pedidos" in payload:
        escribir_valor_configuracion_ecom(
            base_empresa,
            KEY_BACKORDER_EN_PEDIDOS,
            _bool_a_si_no(payload.get("backorder_en_pedidos")),
        )
    for field, key in (
        ("umbral_monto", KEY_APROBACION_UMBRAL_MONTO),
        ("umbral_desc_pie", KEY_APROBACION_UMBRAL_DESC_PIE),
        ("umbral_desc_renglon", KEY_APROBACION_UMBRAL_DESC_RENGLON),
    ):
        if field in payload:
            escribir_valor_configuracion_ecom(
                base_empresa,
                key,
                _normalizar_umbral_texto(payload.get(field)),
            )
    return leer_config_workflow_comercial(base_empresa)


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
        KEY_WORKFLOW_JERARQUIA_COMERCIAL: "Workflow jerarquía comercial",
        KEY_APROBACION_PEDIDOS_ACTIVA: "Aprobación comercial de pedidos",
        KEY_APROBACION_UMBRAL_MONTO: "Umbral monto aprobación pedidos",
        KEY_APROBACION_UMBRAL_DESC_PIE: "Umbral descuento pie aprobación",
        KEY_APROBACION_UMBRAL_DESC_RENGLON: "Umbral descuento renglón aprobación",
        KEY_OBJETIVOS_EN_PEDIDOS: "Atajo objetivos en hub pedidos",
        KEY_BACKORDER_EN_PEDIDOS: "Atajo backorder en hub pedidos",
    }
    detalles = {
        KEY_VALIDAR_STOCK_PEDIDOS: (
            "Si: bloquea PED sin disponible. No: permite PED sin stock (p.ej. fabricación MPR)."
        ),
        KEY_WORKFLOW_JERARQUIA_COMERCIAL: (
            "Si: alcance comercial vía organigrama G→S→V. No: carteras JSON legacy."
        ),
        KEY_APROBACION_PEDIDOS_ACTIVA: (
            "Si: activa cola de aprobación comercial (requiere workflow jerarquía)."
        ),
        KEY_APROBACION_UMBRAL_MONTO: (
            "Monto total del pedido que dispara aprobación. Vacío = regla inactiva."
        ),
        KEY_APROBACION_UMBRAL_DESC_PIE: (
            "Descuento pie (%) que dispara aprobación. Vacío = regla inactiva."
        ),
        KEY_APROBACION_UMBRAL_DESC_RENGLON: (
            "Descuento renglón (%) que dispara aprobación. Vacío = regla inactiva."
        ),
        KEY_OBJETIVOS_EN_PEDIDOS: (
            "Si: muestra atajo a objetivos de venta desde el hub de pedidos."
        ),
        KEY_BACKORDER_EN_PEDIDOS: (
            "Si: habilita atajo backorder desde el hub de pedidos."
        ),
    }
    es_umbral = key in _WORKFLOW_UMBRAL_KEYS
    return {
        "nombre": (nombres.get(key) or key)[:100],
        "detalle": (detalles.get(key) or "")[:1000],
        "grupo": "Ecom Ventas"[:20],
        "tipo": ("Numero" if es_umbral else "Si/No")[:20],
        "detalle_valor": ("" if es_umbral else "Si-No")[:200],
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
