"""Checks de integridad de asientos."""
from __future__ import annotations

from decimal import Decimal

from core.utils.administranet_types import to_decimal_or_none, to_int_or_none, str_or_default

from contabilidad_audit.services.checks._sql import (
    CENTAVO,
    clasificar_delta,
    filtro_anulados_sql,
    filtro_fechas_sql,
    filtro_periodo_sql,
    id_ejercicio_filtro,
)
from contabilidad_audit.services.resultados import (
    CorridaContexto,
    Diferencia,
    audit_result_error,
    construir_audit_result,
)


def asiento_balanceado(base_empresa, filtros, politica, contexto: CorridaContexto):
    check_id = "asiento_balanceado"
    titulo = "Asiento balanceado (debe = haber)"
    severidad = "alto"
    try:
        id_ejercicio = id_ejercicio_filtro(filtros)
        cur = contexto.cursor
        extra_fecha, params_fecha = filtro_fechas_sql(filtros)
        extra_periodo, params_periodo = filtro_periodo_sql(filtros)
        filtro_anul = filtro_anulados_sql(politica)
        cur.execute(
            f"""
            SELECT a.codigo_movimiento,
                   SUM(COALESCE(a.debe_asiento, 0)) AS sum_debe,
                   SUM(COALESCE(a.haber_asiento, 0)) AS sum_haber,
                   MIN(a.nro_asiento) AS nro_asiento
            FROM cont_asiento a
            WHERE a.id_ejercicio = %s
              AND COALESCE(a.codigo_movimiento, 0) <> 0
              {filtro_anul}
              {extra_fecha}
              {extra_periodo}
            GROUP BY a.codigo_movimiento
            """,
            [id_ejercicio, *params_fecha, *params_periodo],
        )
        rows = cur.fetchall()
        diferencias: list[Diferencia] = []
        compensaciones: list[dict] = []
        for row in rows:
            codigo_mov = str_or_default(row[0])
            sum_debe = to_decimal_or_none(row[1]) or Decimal("0")
            sum_haber = to_decimal_or_none(row[2]) or Decimal("0")
            delta = sum_debe - sum_haber
            reportar, tipo = clasificar_delta(delta, politica)
            if not reportar:
                if tipo == "compensacion_centavo":
                    compensaciones.append(
                        {
                            "codigo_movimiento": codigo_mov,
                            "delta": str(delta),
                            "sum_debe": str(sum_debe),
                            "sum_haber": str(sum_haber),
                        }
                    )
                continue
            diferencias.append(
                Diferencia(
                    codigo_movimiento=codigo_mov,
                    nro_asiento=to_int_or_none(row[3]),
                    id_ejercicio=id_ejercicio,
                    valor_esperado=sum_haber,
                    valor_actual=sum_debe,
                    delta=delta,
                    referencia_hallazgo="H09",
                    detalle={"sum_debe": str(sum_debe), "sum_haber": str(sum_haber)},
                )
            )
        return construir_audit_result(
            check_id=check_id,
            titulo=titulo,
            severidad=severidad,
            ok=len(diferencias) == 0,
            total_evaluado=len(rows),
            diferencias=diferencias,
            resumen={"id_ejercicio": id_ejercicio, "centavo_fijo": str(CENTAVO)},
            contexto=contexto,
            compensaciones_centavo=compensaciones or None,
        )
    except Exception as exc:
        return audit_result_error(
            check_id=check_id, titulo=titulo, severidad=severidad, contexto=contexto, mensaje=str(exc)
        )


asiento_balanceado.check_id = "asiento_balanceado"
asiento_balanceado.titulo = "Asiento balanceado (debe = haber)"
asiento_balanceado.severidad = "alto"


def imputacion_a_no_imputable(base_empresa, filtros, politica, contexto: CorridaContexto):
    check_id = "imputacion_a_no_imputable"
    titulo = "Imputación a cuenta no imputable"
    severidad = "alto"
    try:
        id_ejercicio = id_ejercicio_filtro(filtros)
        cur = contexto.cursor
        extra_fecha, params_fecha = filtro_fechas_sql(filtros)
        extra_periodo, params_periodo = filtro_periodo_sql(filtros)
        cur.execute(
            f"""
            SELECT a.codigo_movimiento, a.id_pc, pc.cod_pc, a.nro_asiento
            FROM cont_asiento a
            JOIN cont_pc pc ON pc.id_pc = a.id_pc
            WHERE a.id_ejercicio = %s
              AND COALESCE(pc.imp_cont_pc, '') <> 'Imputable'
              {extra_fecha}
              {extra_periodo}
            """,
            [id_ejercicio, *params_fecha, *params_periodo],
        )
        rows = cur.fetchall()
        diferencias = [
            Diferencia(
                codigo_movimiento=str_or_default(r[0]),
                id_pc=to_int_or_none(r[1]),
                cod_pc=str_or_default(r[2]),
                nro_asiento=to_int_or_none(r[3]),
                id_ejercicio=id_ejercicio,
                referencia_hallazgo="H15",
            )
            for r in rows
        ]
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


imputacion_a_no_imputable.check_id = "imputacion_a_no_imputable"
imputacion_a_no_imputable.titulo = "Imputación a cuenta no imputable"
imputacion_a_no_imputable.severidad = "alto"


def nro_asiento_duplicado(base_empresa, filtros, politica, contexto: CorridaContexto):
    check_id = "nro_asiento_duplicado"
    titulo = "Número de asiento duplicado en ejercicio"
    severidad = "alto"
    try:
        id_ejercicio = id_ejercicio_filtro(filtros)
        cur = contexto.cursor
        cur.execute(
            """
            SELECT nro_asiento, COUNT(DISTINCT codigo_movimiento) AS cant_cm,
                   GROUP_CONCAT(DISTINCT codigo_movimiento) AS codigos
            FROM cont_asiento
            WHERE id_ejercicio = %s AND nro_asiento IS NOT NULL
            GROUP BY nro_asiento
            HAVING cant_cm > 1
            """,
            (id_ejercicio,),
        )
        rows = cur.fetchall()
        diferencias = [
            Diferencia(
                nro_asiento=to_int_or_none(r[0]),
                id_ejercicio=id_ejercicio,
                referencia_hallazgo="H06",
                detalle={"codigos_movimiento": str_or_default(r[2]), "cantidad": to_int_or_none(r[1])},
            )
            for r in rows
        ]
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


nro_asiento_duplicado.check_id = "nro_asiento_duplicado"
nro_asiento_duplicado.titulo = "Número de asiento duplicado en ejercicio"
nro_asiento_duplicado.severidad = "alto"


def codigo_movimiento_huerfano(base_empresa, filtros, politica, contexto: CorridaContexto):
    check_id = "codigo_movimiento_huerfano"
    titulo = "Código de movimiento huérfano (CC sin asiento)"
    severidad = "alto"
    try:
        id_ejercicio = id_ejercicio_filtro(filtros)
        cur = contexto.cursor
        cur.execute(
            """
            SELECT DISTINCT cc.codigo_movimiento
            FROM cont_cc_asiento cc
            LEFT JOIN cont_asiento a
              ON a.codigo_movimiento = cc.codigo_movimiento
             AND a.id_ejercicio = %s
            WHERE a.id_asiento IS NULL
              AND COALESCE(cc.codigo_movimiento, 0) <> 0
            """,
            (id_ejercicio,),
        )
        rows = cur.fetchall()
        diferencias = [
            Diferencia(
                codigo_movimiento=str_or_default(r[0]),
                id_ejercicio=id_ejercicio,
                referencia_hallazgo="H08",
            )
            for r in rows
        ]
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


codigo_movimiento_huerfano.check_id = "codigo_movimiento_huerfano"
codigo_movimiento_huerfano.titulo = "Código de movimiento huérfano (CC sin asiento)"
codigo_movimiento_huerfano.severidad = "alto"
