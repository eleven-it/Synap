"""Checks de cierre y centros de costo."""
from __future__ import annotations

from decimal import Decimal

from core.utils.administranet_types import to_decimal_or_none, to_int_or_none, str_or_default

from contabilidad_audit.services.checks._sql import (
    clasificar_delta,
    cod_pc_coincide_prefijo,
    delta_decimal,
    id_ejercicio_filtro,
)
from contabilidad_audit.services.resultados import (
    CorridaContexto,
    Diferencia,
    audit_result_error,
    construir_audit_result,
)


def cierre_resultado_no_cero(base_empresa, filtros, politica, contexto: CorridaContexto):
    check_id = "cierre_resultado_no_cero"
    titulo = "Cuentas de resultado con saldo residual post-cierre"
    severidad = "medio"
    try:
        id_ejercicio = id_ejercicio_filtro(filtros)
        prefijos = (politica.get("prefijos_cuenta") or {}).get("resultado") or ["4"]
        cur = contexto.cursor
        cur.execute(
            """
            SELECT esc.id_pc, pc.cod_pc, esc.saldo_ejercicio_cta
            FROM cont_ejercicio_saldo_cta esc
            JOIN cont_pc pc ON pc.id_pc = esc.id_pc
            WHERE esc.id_ejercicio = %s
            """,
            (id_ejercicio,),
        )
        rows = cur.fetchall()
        diferencias: list[Diferencia] = []
        for row in rows:
            cod_pc = str_or_default(row[1])
            if not cod_pc_coincide_prefijo(cod_pc, prefijos):
                continue
            saldo = to_decimal_or_none(row[2]) or Decimal("0")
            reportar, _ = clasificar_delta(saldo, politica)
            if reportar:
                diferencias.append(
                    Diferencia(
                        id_pc=to_int_or_none(row[0]),
                        cod_pc=cod_pc,
                        id_ejercicio=id_ejercicio,
                        valor_actual=saldo,
                        delta=saldo,
                        referencia_hallazgo="H11",
                    )
                )
        return construir_audit_result(
            check_id=check_id,
            titulo=titulo,
            severidad=severidad,
            ok=len(diferencias) == 0,
            total_evaluado=len(rows),
            diferencias=diferencias,
            resumen={"id_ejercicio": id_ejercicio, "prefijos_resultado": prefijos},
            contexto=contexto,
        )
    except Exception as exc:
        return audit_result_error(
            check_id=check_id, titulo=titulo, severidad=severidad, contexto=contexto, mensaje=str(exc)
        )


cierre_resultado_no_cero.check_id = "cierre_resultado_no_cero"
cierre_resultado_no_cero.titulo = "Cuentas de resultado con saldo residual post-cierre"
cierre_resultado_no_cero.severidad = "medio"


def reparto_cc_incompleto(base_empresa, filtros, politica, contexto: CorridaContexto):
    check_id = "reparto_cc_incompleto"
    titulo = "Reparto de centro de costo incompleto"
    severidad = "medio"
    try:
        id_ejercicio = id_ejercicio_filtro(filtros)
        cur = contexto.cursor
        cur.execute(
            """
            SELECT a.codigo_movimiento, a.id_pc, a.debe_asiento, a.haber_asiento,
                   COALESCE(SUM(cc.importe_cc), 0) AS sum_cc
            FROM cont_asiento a
            LEFT JOIN cont_cc_asiento cc ON cc.codigo_movimiento = a.codigo_movimiento
                                        AND cc.id_pc = a.id_pc
            WHERE a.id_ejercicio = %s
              AND COALESCE(a.codigo_movimiento, 0) <> 0
            GROUP BY a.codigo_movimiento, a.id_pc, a.debe_asiento, a.haber_asiento
            HAVING SUM(CASE WHEN cc.id_cc_asiento IS NOT NULL THEN 1 ELSE 0 END) > 0
            """,
            (id_ejercicio,),
        )
        rows = cur.fetchall()
        diferencias: list[Diferencia] = []
        for row in rows:
            debe = to_decimal_or_none(row[2]) or Decimal("0")
            haber = to_decimal_or_none(row[3]) or Decimal("0")
            importe_renglon = max(debe, haber)
            sum_cc = to_decimal_or_none(row[4]) or Decimal("0")
            delta = delta_decimal(importe_renglon, sum_cc)
            if delta is None:
                continue
            reportar, _ = clasificar_delta(delta, politica)
            if reportar:
                diferencias.append(
                    Diferencia(
                        codigo_movimiento=str_or_default(row[0]),
                        id_pc=to_int_or_none(row[1]),
                        id_ejercicio=id_ejercicio,
                        valor_esperado=importe_renglon,
                        valor_actual=sum_cc,
                        delta=delta,
                        referencia_hallazgo="H43",
                    )
                )
        return construir_audit_result(
            check_id=check_id,
            titulo=titulo,
            severidad=severidad,
            ok=len(diferencias) == 0,
            total_evaluado=len(rows),
            diferencias=diferencias,
            resumen={"id_ejercicio": id_ejercicio},
            contexto=contexto,
        )
    except Exception as exc:
        return audit_result_error(
            check_id=check_id, titulo=titulo, severidad=severidad, contexto=contexto, mensaje=str(exc)
        )


reparto_cc_incompleto.check_id = "reparto_cc_incompleto"
reparto_cc_incompleto.titulo = "Reparto de centro de costo incompleto"
reparto_cc_incompleto.severidad = "medio"
