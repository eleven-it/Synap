"""
Creación de puntos de venta (PV) fiel a administraNET VB6 CargaPV.frm.
Al crear un PV se inserta en punto_venta y se crean los 38 talonarios (uno por tipo de comprobante).
Opcionalmente se insertan filas en reporte_comprobante si la tabla existe.
"""
import logging
from datetime import date
from typing import Optional, Tuple

from self_checkout.db import mysql_cursor
from self_checkout.services.talonarios_service import TIPOS_COMPROBANTE, crear_talonario

logger = logging.getLogger(__name__)


def existe_nro_pv(base_empresa: str, nro_punto_venta: str) -> bool:
    """True si ya existe un punto de venta con ese nro_punto_venta."""
    try:
        with mysql_cursor(base_empresa, dict_cursor=True) as c:
            c.execute(
                "SELECT 1 FROM punto_venta WHERE nro_punto_venta = %s LIMIT 1",
                [nro_punto_venta.strip()],
            )
            return c.fetchone() is not None
    except Exception as e:
        logger.warning("existe_nro_pv failed: %s", e)
        return True  # en duda no crear


def crear_punto_venta(
    base_empresa: str,
    nro_punto_venta: str,
    id_sucursal: int,
) -> Tuple[Optional[int], str]:
    """
    Crea un nuevo punto de venta y sus 38 talonarios (fiel a CargaPV.frm).
    Returns: (id_punto_venta, '') si OK, (None, mensaje_error) si falla.
    """
    nro = (nro_punto_venta or "").strip()
    if not nro:
        return None, "El número de punto de venta es obligatorio."
    if existe_nro_pv(base_empresa, nro):
        return None, "Ya existe un punto de venta con ese número."
    if not id_sucursal:
        return None, "Debe seleccionar una sucursal."

    try:
        with mysql_cursor(base_empresa) as c:
            # INSERT punto_venta: campos mínimos como en VB6 (el resto puede tener default)
            try:
                c.execute(
                    """
                    INSERT INTO punto_venta
                    (nro_punto_venta, id_sucursal, lista_precio_pv, fe_regimen,
                     ruta_reporte_comprobante, ruta_certificado, ruta_certificado_local,
                     bloquea_descuento_pie, fe_regimen_tipo, tpv_venta_x_bulto, utiliza_regla_precio)
                    VALUES (%s, %s, 0, 'No', '', '', '', 'No', 'No', 'No', 'No')
                    """,
                    [nro, id_sucursal],
                )
            except Exception as e:
                # Si la tabla no tiene esas columnas, intentar solo las obligatorias
                logger.debug("punto_venta insert with full fields failed: %s", e)
                c.execute(
                    "INSERT INTO punto_venta (nro_punto_venta, id_sucursal) VALUES (%s, %s)",
                    [nro, id_sucursal],
                )
            c.execute("SELECT LAST_INSERT_ID() AS id")
            row = c.fetchone()
            id_pv = int(row[0]) if row else None
            if not id_pv:
                return None, "No se pudo obtener el ID del punto de venta creado."

            # reporte_comprobante: opcional (tabla puede no existir o tener otra estructura)
            try:
                for i, tipo in enumerate(TIPOS_COMPROBANTE):
                    detalle = (
                        "Declaro que los datos consignados en este formulario son correctos y completos, que he confeccionado la presente utilizando la aplicación"
                        if tipo in ("RETIB", "RETG", "POE")
                        else "Gracias por su compra.... - Defensa al Consumidor"
                    )
                    c.execute(
                        """
                        INSERT INTO reporte_comprobante
                        (nombre_reporte_comprobante, nombre_impresora, numero_copias, detalle_comprobante, id_sucursal, id_punto_venta)
                        VALUES (%s, 'Ventana', 2, %s, %s, %s)
                        """,
                        [tipo, detalle, id_sucursal, id_pv],
                    )
            except Exception as e:
                logger.info("reporte_comprobante insert skipped (table may not exist): %s", e)

            # Talonarios: uno por cada tipo (como CargaPV For i = 0 To 37)
            hoy = date.today()
            for tipo in TIPOS_COMPROBANTE:
                ok = crear_talonario(
                    base_empresa,
                    id_pv,
                    tipo,
                    nro_inic=1,
                    nro_final=5000,
                    nro_cai="00000000000000",
                    fecha_cai=hoy,
                )
                if not ok:
                    logger.warning("crear_talonario %s for PV %s failed", tipo, id_pv)
            return id_pv, ""
    except Exception as e:
        logger.exception("crear_punto_venta failed: %s", e)
        return None, str(e) or "Error al crear el punto de venta."
