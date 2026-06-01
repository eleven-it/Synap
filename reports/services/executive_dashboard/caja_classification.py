"""Clasificación y SQL compartido de movimientos de caja (Command Center + cash flow)."""
from __future__ import annotations

from typing import Tuple


def is_movimiento_interno(tipo: str | None) -> bool:
    """Transferencias entre cajas y cierres — excluir del neto consolidado."""
    if not tipo:
        return False
    t = tipo.lower()
    return "cierre de caja" in t or "transferencia de fondos" in t


def is_movimiento_no_operativo(tipo: str | None) -> bool:
    """Internos + inversión/financiamiento (paridad cash_flow_waterfall)."""
    if is_movimiento_interno(tipo):
        return True
    if not tipo:
        return False
    t = tipo.lower()
    return any(
        k in t
        for k in (
            "inversión",
            "inversion",
            "activo fijo",
            "préstamo",
            "prestamo",
            "aporte",
            "capital",
        )
    )


def sql_no_operativo_predicado(campo: str = "c.tipo") -> str:
    """Fragmento SQL: verdadero si el movimiento no es flujo operativo."""
    return f"""(
        {campo} LIKE '%%Cierre de Caja%%'
        OR {campo} LIKE '%%Transferencia de Fondos%%'
        OR {campo} LIKE '%%Inversión%%'
        OR {campo} LIKE '%%Activo Fijo%%'
        OR {campo} LIKE '%%Préstamo%%'
        OR {campo} LIKE '%%Aporte%%'
        OR {campo} LIKE '%%Capital%%'
    )"""


def sql_es_flujo_operativo(campo: str = "c.tipo") -> str:
    """CASE 1/0: cuenta en flujo operativo consolidado."""
    return f"CASE WHEN {sql_no_operativo_predicado(campo)} THEN 0 ELSE 1 END"


def sql_excluir_interno_campo(campo: str = "c.tipo") -> str:
    """Fragmento SQL: 1 si operativo externo, 0 si cierre/transferencia."""
    return (
        f"CASE WHEN {campo} LIKE '%%Cierre de Caja%%' "
        f"OR {campo} LIKE '%%Transferencia de Fondos%%' THEN 0 ELSE 1 END"
    )


def sql_predicado_ingresos_ventas(
    campo_comp: str = "c.tipo_comprobante",
    campo_tipo: str = "c.tipo",
) -> str:
    return f"""(
        {campo_comp} IN ('FA','FB','FC','FE','FM','TARJ')
    )"""


def sql_predicado_ingresos_cobranzas(
    campo_comp: str = "c.tipo_comprobante",
    campo_tipo: str = "c.tipo",
    campo_cp: str = "c.tipo_cp",
) -> str:
    return f"""(
        {campo_comp} = 'REC'
        OR {campo_comp} = 'OMC'
        OR ({campo_comp} = 'CHEQ' AND (
            {campo_cp} = 'Cliente'
            OR LOWER(COALESCE({campo_tipo}, '')) LIKE '%%cheque%%'
        ))
        OR ({campo_comp} = 'MCAJ' AND (
            LOWER({campo_tipo}) LIKE '%%cobro%%'
            OR LOWER({campo_tipo}) LIKE '%%cobranza%%'
            OR LOWER({campo_tipo}) LIKE '%%ingreso%%'
            OR LOWER({campo_tipo}) LIKE '%%deposito%%'
            OR LOWER({campo_tipo}) LIKE '%%depósito%%'
        ))
    )"""


def sql_predicado_egresos_proveedores(
    campo_comp: str = "c.tipo_comprobante",
    campo_tipo: str = "c.tipo",
    campo_cp: str = "c.tipo_cp",
) -> str:
    """Paridad AdministraNET: OP, compras FA/FB, cheques entregados a proveedor, NCA."""
    return f"""(
        {campo_comp} = 'OP'
        OR {campo_comp} = 'NCA'
        OR ({campo_comp} IN ('FA','FB') AND {campo_cp} = 'Proveedor')
        OR ({campo_comp} = 'CHEQ' AND (
            {campo_cp} = 'Proveedor'
            OR LOWER(COALESCE({campo_tipo}, '')) LIKE '%%entrega proveedor%%'
        ))
    )"""


def sum_saldo_cajas(
    cursor,
    fecha_limite: str,
    *,
    antes_de: bool,
    cod_sucursal: int | None = None,
    id_cajas: list[int] | None = None,
) -> float:
    """Suma último caja.Saldo por id_caja_abm_origen antes o hasta fecha_limite."""
    op = "<" if antes_de else "<="
    suc_sql = ""
    suc_params: list = []
    if cod_sucursal is not None:
        suc_sql = " AND cod_sucursal = %s"
        suc_params = [cod_sucursal]
    caja_sql = ""
    caja_params: list = []
    if id_cajas:
        placeholders = ",".join(["%s"] * len(id_cajas))
        caja_sql = f" AND id_caja_abm_origen IN ({placeholders})"
        caja_params = list(id_cajas)
    base_where = f"""
        anulado = 'No'
        AND id_caja_abm_origen IS NOT NULL
        AND fecha {op} %s
        {suc_sql}
        {caja_sql}
    """
    sql = f"""
        SELECT COALESCE(SUM(c.saldo), 0)
        FROM caja c
        INNER JOIN (
            SELECT id_caja_abm_origen, MAX(fecha) AS max_fecha
            FROM caja
            WHERE {base_where}
            GROUP BY id_caja_abm_origen
        ) ult_f ON ult_f.id_caja_abm_origen = c.id_caja_abm_origen
              AND c.fecha = ult_f.max_fecha
        INNER JOIN (
            SELECT id_caja_abm_origen, fecha, MAX(codigo_movimiento) AS max_mov
            FROM caja
            WHERE {base_where}
            GROUP BY id_caja_abm_origen, fecha
        ) ult_m ON ult_m.id_caja_abm_origen = c.id_caja_abm_origen
              AND ult_m.fecha = c.fecha
              AND ult_m.max_mov = c.codigo_movimiento
        WHERE c.anulado = 'No'
    """
    params = (
        [fecha_limite] + suc_params + caja_params + [fecha_limite] + suc_params + caja_params
    )
    cursor.execute(sql, params)
    row = cursor.fetchone()
    return float(row[0] or 0) if row else 0.0


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
        if tipo_comp_upper == "CHEQ" and (
            tipo_cp == "Cliente" or "cheque" in tipo_lower
        ):
            return ("operativo", "ingresos_cobranzas")
        if tipo_comp_upper == "MCAJ":
            if any(
                k in tipo_lower
                for k in ("cobro", "cobranza", "ingreso", "deposito", "depósito")
            ):
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
        if tipo_comp_upper == "CHEQ" and (
            tipo_cp == "Proveedor" or "entrega proveedor" in tipo_lower
        ):
            return ("operativo", "egresos_proveedores")
        if tipo_comp_upper == "CHEQ":
            return ("operativo", "egresos_otros")
        if tipo_comp_upper == "MCAJ":
            if any(
                k in tipo_lower
                for k in (
                    "pago",
                    "egreso",
                    "extraccion",
                    "extracción",
                    "entrega",
                    "retiro",
                )
            ):
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
