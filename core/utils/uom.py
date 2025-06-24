from decimal import Decimal

def convert_qty(qty: Decimal, from_uom, to_uom):
    """
    Convierte una cantidad entre unidades de la misma categoría.
    :param qty: cantidad original
    :param from_uom: instancia de UnitOfMeasure origen
    :param to_uom: instancia de UnitOfMeasure destino
    :return: cantidad convertida
    """
    if from_uom.category != to_uom.category:
        raise ValueError("Las unidades no pertenecen a la misma categoría")

    return qty * (from_uom.ratio / to_uom.ratio)

def is_reference_uom(uom):
    return uom.is_reference
