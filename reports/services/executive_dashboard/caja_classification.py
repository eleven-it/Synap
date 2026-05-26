"""Clasificación de movimientos de caja (paridad query_runner)."""
from __future__ import annotations

from typing import Tuple


def is_movimiento_interno(tipo: str | None) -> bool:
    """Transferencias entre cajas y cierres — excluir del neto consolidado."""
    if not tipo:
        return False
    t = tipo.lower()
    return "cierre de caja" in t or "transferencia de fondos" in t


def classify_movement(
    tipo_comprobante,
    tipo,
    ingreso,
    egreso,
    tipo_cp=None,
    cod_gasto=None,
    gasto_nombre=None,
    grupo_gasto_nombre=None,
) -> Tuple[str, str]:
    """
    Clasifica movimiento en (flujo_tipo, flujo_subcategoria).
    Paridad: QueryRunnerService._classify_movement.
    """
    tipo_comp_upper = tipo_comprobante.upper() if tipo_comprobante else ""
    tipo_lower = tipo.lower() if tipo else ""

    if ingreso and float(ingreso) > 0:
        if tipo_comp_upper in ("FA", "FB", "FC", "FE", "FM"):
            return ("operativo", "ingresos_ventas")
        if tipo_comp_upper in ("REC",):
            return ("operativo", "ingresos_cobranzas")
        if tipo_comp_upper == "CHEQ" and tipo_cp == "Cliente":
            return ("operativo", "ingresos_cobranzas")
        if tipo_comp_upper == "MCAJ":
            if any(k in tipo_lower for k in ("cobro", "cobranza", "ingreso", "deposito", "depósito")):
                return ("operativo", "ingresos_cobranzas")
            return ("operativo", "ingresos_otros")
        if tipo_comp_upper == "TARJ":
            return ("operativo", "ingresos_ventas")
        if tipo_comp_upper == "OMC":
            return ("operativo", "ingresos_cobranzas")
        if "interes" in tipo_lower or "interés" in tipo_lower:
            return ("operativo", "ingresos_intereses")
        return ("operativo", "ingresos_otros")

    if egreso and float(egreso) > 0:
        if tipo_comp_upper in ("FA", "FB") and tipo_cp == "Proveedor":
            return ("operativo", "egresos_proveedores")
        if tipo_comp_upper == "OP":
            if tipo_cp == "Proveedor":
                return ("operativo", "egresos_proveedores")
            return ("operativo", "egresos_otros")
        if tipo_comp_upper == "CHEQ" and tipo_cp == "Proveedor":
            return ("operativo", "egresos_proveedores")
        if tipo_comp_upper == "CHEQ":
            return ("operativo", "egresos_otros")
        if tipo_comp_upper == "MCAJ":
            if any(k in tipo_lower for k in ("pago", "egreso", "extraccion", "extracción", "entrega")):
                if tipo_cp == "Proveedor":
                    return ("operativo", "egresos_proveedores")
                return ("operativo", "egresos_otros")
            return ("operativo", "egresos_otros")
        if tipo_comp_upper == "NCA":
            return ("operativo", "egresos_proveedores")
        if cod_gasto and float(cod_gasto) > 0:
            return ("operativo", "egresos_gastos")
        if "sueldo" in tipo_lower or "salario" in tipo_lower:
            return ("operativo", "egresos_sueldos")
        if "impuesto" in tipo_lower or "iva" in tipo_lower:
            return ("operativo", "egresos_impuestos")
        if "servicio" in tipo_lower:
            return ("operativo", "egresos_servicios")
        return ("operativo", "egresos_otros")

    return ("operativo", "otros")


def get_payment_method(tipo_comprobante, tipo) -> str:
    """Medio de pago heurístico. Paridad: QueryRunnerService._get_payment_method."""
    tipo_comp_upper = tipo_comprobante.upper() if tipo_comprobante else ""
    tipo_comp_lower = tipo_comprobante.lower() if tipo_comprobante else ""
    tipo_lower = tipo.lower() if tipo else ""

    if tipo_comp_upper == "CHEQ" or "cheque" in tipo_comp_lower or "cheq" in tipo_comp_lower:
        return "Cheque"
    if tipo_comp_upper == "TARJ" or "tarjeta" in tipo_lower:
        return "Tarjeta"
    if tipo_comp_upper == "MCAJ":
        if "efectivo" in tipo_lower:
            return "Efectivo"
        if "cheque" in tipo_lower or "cheq" in tipo_lower:
            return "Cheque"
        if "transferencia" in tipo_lower:
            return "Transferencia"
        if "deposito" in tipo_lower or "depósito" in tipo_lower:
            return "Depósito"
        return "Movimiento de Caja"
    if tipo_comp_upper == "REC":
        if "efectivo" in tipo_lower:
            return "Efectivo"
        if "cheque" in tipo_lower:
            return "Cheque"
        return "Recibo"
    if tipo_comp_upper == "OP":
        if "efectivo" in tipo_lower:
            return "Efectivo"
        if "cheque" in tipo_lower:
            return "Cheque"
        return "Orden de Pago"
    if "efectivo" in tipo_lower:
        return "Efectivo"
    if "transferencia" in tipo_lower:
        return "Transferencia"
    if "deposito" in tipo_lower or "depósito" in tipo_lower:
        return "Depósito"
    return tipo_comprobante if tipo_comprobante else "Otro"


def medio_cobro_bucket(medio: str) -> str:
    """Mapea etiqueta de medio a bucket API ventas_cobros."""
    m = (medio or "").lower()
    if m == "efectivo":
        return "efectivo"
    if m == "tarjeta":
        return "tarjeta"
    if m == "cheque":
        return "cheque"
    if m in ("transferencia", "depósito", "deposito"):
        return "transferencia"
    return "otros"


def sql_excluir_interno_campo(campo: str = "c.tipo") -> str:
    """Fragmento SQL: 1 si operativo, 0 si movimiento interno."""
    return (
        f"CASE WHEN {campo} LIKE '%%Cierre de Caja%%' "
        f"OR {campo} LIKE '%%Transferencia de Fondos%%' THEN 0 ELSE 1 END"
    )
