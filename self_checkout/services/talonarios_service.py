"""
Servicio de talonarios (puntos de venta y numeración por tipo de comprobante).
Fiel a administraNET VB6: ABMTalonario.frm, CargaTalonarios.frm, CargaPV.frm.
Tabla: talonarios (id_punto_venta, TipoComprobante, Nro, NroInic, NroFinal, NroCAI, FechaCAI, Nro_Credito, Orden, ...).
"""
import logging
from datetime import date
from typing import Any, Dict, List, Optional

from self_checkout.db import mysql_cursor

logger = logging.getLogger(__name__)

# Tipos de comprobante que se pueden tener en talonarios (como en CargaPV Array_Comprobante)
TIPOS_COMPROBANTE = [
    "FA", "FB", "FC", "FE", "FM",
    "NCA", "NCB", "NCC", "NCE", "NCM",
    "NDA", "NDB", "NDC", "NDE", "NDM",
    "REC", "OP", "PRE", "PED", "REM",
    "RETIB", "RETG", "MCAJ", "MSTOCK", "AJ",
    "OC", "PEDI", "EB", "CHEQUE", "PD",
    "OE", "PREP", "POE", "RETIVA", "DEV",
    "PSJ", "VALE", "CI-COMOD",
]


def listar_talonarios_por_pv(base_empresa: str, id_punto_venta: int) -> List[Dict[str, Any]]:
    """Lista filas de talonarios para un punto de venta. Orden por Orden o por TipoComprobante."""
    try:
        with mysql_cursor(base_empresa, dict_cursor=True) as c:
            # Orden como en VB6: order by Orden (si existe la columna)
            try:
                c.execute("""
                    SELECT id_punto_venta, TipoComprobante, Nro,
                           COALESCE(NroInic, 1) AS NroInic, COALESCE(NroFinal, 5000) AS NroFinal,
                           NroCAI, FechaCAI, COALESCE(Nro_Credito, 1) AS Nro_Credito,
                           COALESCE(Orden, 0) AS Orden
                    FROM talonarios
                    WHERE id_punto_venta = %s
                    ORDER BY Orden, TipoComprobante
                """, [id_punto_venta])
            except Exception:
                c.execute("""
                    SELECT id_punto_venta, TipoComprobante, Nro,
                           COALESCE(NroInic, 1) AS NroInic, COALESCE(NroFinal, 5000) AS NroFinal,
                           NroCAI, FechaCAI, COALESCE(Nro_Credito, 1) AS Nro_Credito
                    FROM talonarios
                    WHERE id_punto_venta = %s
                    ORDER BY TipoComprobante
                """, [id_punto_venta])
            rows = c.fetchall()
            return [dict(r) for r in rows]
    except Exception as e:
        logger.warning("listar_talonarios_por_pv failed: %s", e)
        return []


def obtener_talonario(base_empresa: str, id_punto_venta: int, tipo_comprobante: str) -> Optional[Dict[str, Any]]:
    """Obtiene una fila de talonarios por PV y tipo."""
    try:
        with mysql_cursor(base_empresa, dict_cursor=True) as c:
            c.execute("""
                SELECT id_punto_venta, TipoComprobante, Nro,
                       COALESCE(NroInic, 1) AS NroInic, COALESCE(NroFinal, 5000) AS NroFinal,
                       NroCAI, FechaCAI, COALESCE(Nro_Credito, 1) AS Nro_Credito
                FROM talonarios
                WHERE id_punto_venta = %s AND TipoComprobante = %s
            """, [id_punto_venta, tipo_comprobante])
            row = c.fetchone()
            return dict(row) if row else None
    except Exception as e:
        logger.warning("obtener_talonario failed: %s", e)
        return None


def actualizar_talonario(
    base_empresa: str,
    id_punto_venta: int,
    tipo_comprobante: str,
    nro: int,
    nro_inic: Optional[int] = None,
    nro_final: Optional[int] = None,
    nro_cai: Optional[str] = None,
    fecha_cai: Optional[date] = None,
    nro_credito: Optional[int] = None,
) -> bool:
    """Actualiza Nro, NroInic, NroFinal, NroCAI, FechaCAI, Nro_Credito (como CargaTalonarios Guardar)."""
    try:
        with mysql_cursor(base_empresa) as c:
            # Campos opcionales: solo actualizar los que existen
            updates = ["Nro = %s"]
            params = [nro]
            if nro_inic is not None:
                updates.append("NroInic = %s")
                params.append(nro_inic)
            if nro_final is not None:
                updates.append("NroFinal = %s")
                params.append(nro_final)
            if nro_cai is not None:
                updates.append("NroCAI = %s")
                params.append(nro_cai)
            if fecha_cai is not None:
                updates.append("FechaCAI = %s")
                params.append(fecha_cai)
            if nro_credito is not None:
                updates.append("Nro_Credito = %s")
                params.append(nro_credito)
            params.extend([id_punto_venta, tipo_comprobante])
            c.execute(
                f"UPDATE talonarios SET {', '.join(updates)} WHERE id_punto_venta = %s AND TipoComprobante = %s",
                params,
            )
            return c.rowcount > 0
    except Exception as e:
        logger.exception("actualizar_talonario failed: %s", e)
        return False


def tipos_faltantes_para_pv(base_empresa: str, id_punto_venta: int) -> List[str]:
    """Tipos de comprobante que aún no tienen talonario para este PV (para agregar)."""
    existentes = {r["TipoComprobante"] for r in listar_talonarios_por_pv(base_empresa, id_punto_venta)}
    return [t for t in TIPOS_COMPROBANTE if t not in existentes]


def siguiente_orden(base_empresa: str, id_punto_venta: int) -> int:
    """MAX(Orden)+1 para el PV, o 1 si no hay columna Orden."""
    try:
        with mysql_cursor(base_empresa, dict_cursor=True) as c:
            c.execute(
                "SELECT COALESCE(MAX(Orden), 0) + 1 AS next_orden FROM talonarios WHERE id_punto_venta = %s",
                [id_punto_venta],
            )
            row = c.fetchone()
            return int(row["next_orden"]) if row and row.get("next_orden") is not None else 1
    except Exception:
        return 1


def crear_talonario(
    base_empresa: str,
    id_punto_venta: int,
    tipo_comprobante: str,
    nro_inic: int = 1,
    nro_final: int = 5000,
    nro_cai: str = "00000000000000",
    fecha_cai: Optional[date] = None,
) -> bool:
    """
    Inserta un talonario para el PV y tipo (como en CargaPV al agregar PV).
    Nro = nro_inic, Nro_Credito = 1. Orden = siguiente_orden.
    """
    if tipo_comprobante not in TIPOS_COMPROBANTE:
        return False
    from datetime import date as date_type
    fecha = fecha_cai or date_type.today()
    orden = siguiente_orden(base_empresa, id_punto_venta)
    try:
        with mysql_cursor(base_empresa) as c:
            try:
                c.execute(
                    """
                    INSERT INTO talonarios
                    (id_punto_venta, TipoComprobante, Nro, NroInic, NroFinal, NroCAI, FechaCAI, Nro_Credito, Orden)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, 1, %s)
                    """,
                    [id_punto_venta, tipo_comprobante, nro_inic, nro_inic, nro_final, nro_cai, fecha, orden],
                )
            except Exception:
                c.execute(
                    """
                    INSERT INTO talonarios
                    (id_punto_venta, TipoComprobante, Nro, NroInic, NroFinal, NroCAI, FechaCAI, Nro_Credito)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, 1)
                    """,
                    [id_punto_venta, tipo_comprobante, nro_inic, nro_inic, nro_final, nro_cai, fecha],
                )
            return True
    except Exception as e:
        logger.exception("crear_talonario failed: %s", e)
        return False
