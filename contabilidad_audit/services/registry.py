"""Registry de checks de auditoría contable."""
from contabilidad_audit.services.checks.asientos import (
    asiento_balanceado,
    codigo_movimiento_huerfano,
    imputacion_a_no_imputable,
    nro_asiento_duplicado,
)
from contabilidad_audit.services.checks.cierres import (
    cierre_resultado_no_cero,
    reparto_cc_incompleto,
)
from contabilidad_audit.services.checks.compras_pagos import (
    asiento_compra_pago_desbalanceado_saldo_null,
    comprobante_compra_pago_sin_asiento,
    integridad_anulacion_compra_pago,
)
from contabilidad_audit.services.checks.conceptos import (
    concepto_anulacion_incoherente,
    concepto_no_normal,
)
from contabilidad_audit.services.checks.periodos import (
    fecha_fuera_de_periodo,
    periodos_solapados,
)
from contabilidad_audit.services.checks.rei import rei_recalculo
from contabilidad_audit.services.checks.saldos import (
    cuentas_sin_fila_saldo,
    saldo_ejercicio_vs_diario,
    saldo_periodo_vs_diario,
)
from contabilidad_audit.services.resultados import Check

CHECKS: dict[str, Check] = {
    "asiento_balanceado": asiento_balanceado,
    "saldo_ejercicio_vs_diario": saldo_ejercicio_vs_diario,
    "saldo_periodo_vs_diario": saldo_periodo_vs_diario,
    "cuentas_sin_fila_saldo": cuentas_sin_fila_saldo,
    "imputacion_a_no_imputable": imputacion_a_no_imputable,
    "concepto_anulacion_incoherente": concepto_anulacion_incoherente,
    "nro_asiento_duplicado": nro_asiento_duplicado,
    "codigo_movimiento_huerfano": codigo_movimiento_huerfano,
    "fecha_fuera_de_periodo": fecha_fuera_de_periodo,
    "periodos_solapados": periodos_solapados,
    "cierre_resultado_no_cero": cierre_resultado_no_cero,
    "reparto_cc_incompleto": reparto_cc_incompleto,
    "rei_recalculo": rei_recalculo,
    "concepto_no_normal": concepto_no_normal,
    "comprobante_compra_pago_sin_asiento": comprobante_compra_pago_sin_asiento,
    "asiento_compra_pago_desbalanceado_saldo_null": asiento_compra_pago_desbalanceado_saldo_null,
    "integridad_anulacion_compra_pago": integridad_anulacion_compra_pago,
}

CHECK_IDS_DEFAULT = list(CHECKS.keys())
