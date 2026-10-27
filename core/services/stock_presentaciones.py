"""Reglas de cantidades de administraNET para movimientos y pedidos internos.

Las cantidades de stock y los pendientes se guardan siempre en unidades base.
"""

from decimal import Decimal, InvalidOperation


class PresentacionInvalida(ValueError):
    pass


def _positivo(valor, nombre):
    try:
        numero = Decimal(str(valor))
    except (InvalidOperation, TypeError, ValueError) as exc:
        raise PresentacionInvalida(f"{nombre} inválido.") from exc
    if not numero.is_finite() or numero <= 0:
        raise PresentacionInvalida(f"{nombre} debe ser mayor a cero.")
    return numero


def factor_presentacion(tipo, unidades_display, multiplicador_comp, displays_bulto,
                        *, usa_lote=False, usa_serie=False):
    """Misma prioridad de factores que VB6 Obtener_Factor_Presentacion_Articulo_Seguro."""
    tipo = str(tipo or "Unidad").strip().upper()
    if tipo == "UNIDAD":
        return Decimal(1)
    if usa_lote or usa_serie:
        raise PresentacionInvalida("Los artículos con lote o serie se cargan por Unidad.")
    if tipo == "DISPLAY":
        unidades = _positivo(unidades_display, "Unidades por display")
        if unidades <= 1:
            raise PresentacionInvalida("El artículo no tiene un display mayor a una unidad.")
        return unidades
    if tipo in ("BULTO", "BULTO/PALLET"):
        unidades = _positivo(unidades_display, "Unidades por display")
        multiplicador = Decimal(str(multiplicador_comp or 0))
        if multiplicador <= 0:
            multiplicador = _positivo(displays_bulto, "Displays por bulto")
        if unidades * multiplicador <= 1:
            raise PresentacionInvalida("El artículo no tiene un bulto mayor a una unidad.")
        return unidades * multiplicador
    raise PresentacionInvalida(f"Presentación no reconocida: {tipo}.")


def datos_presentacion_articulo(cursor, id_articulo):
    """El proveedor principal gana; el mismo criterio determinístico del módulo VB6."""
    cursor.execute(
        """SELECT a.IDArt, IFNULL(a.lote,'No'), IFNULL(a.serie,'No'),
                  ap.cantidad_unidad_display, ap.multiplicador_comp,
                  ap.cantidad_display_bulto
           FROM articulo a LEFT JOIN articulo_prov ap ON ap.IDArt=a.IDArt
             AND IFNULL(ap.anulado,'No')='No'
           WHERE a.IDArt=%s
           ORDER BY CASE WHEN ap.CodProveedor=a.CodigoProveedor THEN 0 ELSE 1 END,
                    ap.CodProveedor, ap.id_articulo_prov LIMIT 1""",
        [id_articulo],
    )
    row = cursor.fetchone()
    if not row:
        raise PresentacionInvalida(f"El artículo {id_articulo} no existe.")
    _, lote, serie, unidades_display, multiplicador, displays_bulto = row
    return {
        "lote": str(lote).strip().upper() == "SI",
        "serie": str(serie).strip().upper() == "SI",
        "unidades_display": unidades_display,
        "multiplicador_comp": multiplicador,
        "displays_bulto": displays_bulto,
    }
