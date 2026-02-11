"""
Condición fiscal del emisor (empresa) desde datosempresa.IDIva.
Según administraNET VB6: Lista_Comp_Fact, Lista_Comp_Gral, Exportacion.frm (TipoResponsable).
Usado para decidir tipo de comprobante: RI → FA/FB según cliente; Monotributo/Exento → siempre FC (AFIP).
"""
import logging
from typing import Optional

from self_checkout.db import mysql_cursor

logger = logging.getLogger(__name__)

# Códigos IDIva en datosempresa (administraNET VB6 / AFIP):
# 1 = IVA Responsable Inscripto (RI)     → emite FA o FB según receptor
# 2 = IVA Responsable no Inscripto        → emite FC (Monotributo/Exento)
# 3 = IVA no Responsable                   → emite FC
# 4 = IVA Sujeto Exento                    → emite FC
# 6 = Responsable MONOTRIBUTO               → emite FC
# 7 = Sujeto no Categorizado                → emite FA o FB (tratado como RI en VB6)
IDIVA_EMISOR_RI = {1, 7}  # Emisor puede emitir Factura A o B según cliente
IDIVA_EMISOR_SOLO_FC = {2, 3, 4, 6}  # Emisor solo Factura C (Monotributo/Exento)


def get_id_iva_emisor(base_empresa: str) -> Optional[int]:
    """
    Obtiene el IDIva de la empresa emisora desde datosempresa (tabla DatosEmpresa en administraNET).
    Returns: 1, 2, 3, 4, 6, 7, etc., o None si no se puede obtener (se asume RI por defecto).
    """
    try:
        with mysql_cursor(base_empresa, dict_cursor=True) as c:
            # VB6 usa: SELECT IDIVA FROM datosempresa WHERE id_empresa = 1
            c.execute("""
                SELECT IDIva AS id_iva FROM DatosEmpresa WHERE id_empresa = 1 LIMIT 1
            """)
            row = c.fetchone()
            if row is None:
                # Algunas bases usan minúscula
                c.execute("""
                    SELECT IDIVA AS id_iva FROM datosempresa WHERE id_empresa = 1 LIMIT 1
                """)
                row = c.fetchone()
            if row is not None and row.get("id_iva") is not None:
                return int(row["id_iva"])
    except Exception as e:
        logger.debug("No se pudo leer IDIva emisor desde datosempresa: %s", e)
    return None


def emisor_emite_solo_factura_c(base_empresa: str) -> bool:
    """
    True si la empresa emisora es Monotributo/Exento y por tanto solo debe emitir Factura C (AFIP).
    """
    id_iva = get_id_iva_emisor(base_empresa)
    return id_iva is not None and id_iva in IDIVA_EMISOR_SOLO_FC


def emisor_es_responsable_inscripto(base_empresa: str) -> bool:
    """
    True si la empresa puede emitir Factura A o B según condición del cliente (RI o Sujeto no categorizado).
    """
    id_iva = get_id_iva_emisor(base_empresa)
    if id_iva is None:
        return True  # Por defecto asumir RI (comportamiento actual)
    return id_iva in IDIVA_EMISOR_RI
