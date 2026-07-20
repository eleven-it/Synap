"""Checks de conceptos de asiento."""
from __future__ import annotations

from core.utils.administranet_types import to_int_or_none, str_or_default

from contabilidad_audit.services.checks._sql import id_ejercicio_filtro
from contabilidad_audit.services.resultados import (
    CorridaContexto,
    Diferencia,
    audit_result_error,
    construir_audit_result,
)


def concepto_anulacion_incoherente(base_empresa, filtros, politica, contexto: CorridaContexto):
    check_id = "concepto_anulacion_incoherente"
    titulo = "Concepto de anulación incoherente"
    severidad = "alto"
    try:
        id_ejercicio = id_ejercicio_filtro(filtros)
        cur = contexto.cursor
        cur.execute(
            """
            SELECT o.codigo_movimiento,
                   o.id_concepto_asiento AS concepto_original,
                   c.id_concepto_asiento AS concepto_contra,
                   ca_orig.id_concepto_anul AS concepto_esperado
            FROM cont_asiento o
            JOIN cont_concepto_asiento ca_orig
              ON ca_orig.id_concepto_asiento = o.id_concepto_asiento
            JOIN cont_asiento c
              ON c.codigo_movimiento_anul = o.codigo_movimiento
             AND c.id_ejercicio = o.id_ejercicio
             AND COALESCE(c.anulado, 'No') = 'No'
            WHERE o.id_ejercicio = %s
              AND COALESCE(o.anulado, 'No') = 'Si'
              AND ca_orig.id_concepto_anul IS NOT NULL
              AND c.id_concepto_asiento <> ca_orig.id_concepto_anul
            """,
            (id_ejercicio,),
        )
        rows = cur.fetchall()
        diferencias = [
            Diferencia(
                codigo_movimiento=str_or_default(r[0]),
                id_ejercicio=id_ejercicio,
                referencia_hallazgo="H05",
                detalle={
                    "concepto_original": to_int_or_none(r[1]),
                    "concepto_contra": to_int_or_none(r[2]),
                    "concepto_esperado": to_int_or_none(r[3]),
                },
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


concepto_anulacion_incoherente.check_id = "concepto_anulacion_incoherente"
concepto_anulacion_incoherente.titulo = "Concepto de anulación incoherente"
concepto_anulacion_incoherente.severidad = "alto"


def concepto_no_normal(base_empresa, filtros, politica, contexto: CorridaContexto):
    check_id = "concepto_no_normal"
    titulo = "Concepto no normal en imputaciones"
    severidad = "medio"
    try:
        id_ejercicio = id_ejercicio_filtro(filtros)
        cur = contexto.cursor
        cur.execute(
            """
            SELECT DISTINCT ca.id_concepto_asiento,
                   ca.desc_concepto_asiento,
                   ca.tipo_concepto_asiento,
                   ca.tipo_concepto
            FROM cont_asiento a
            JOIN cont_concepto_asiento ca ON ca.id_concepto_asiento = a.id_concepto_asiento
            WHERE a.id_ejercicio = %s
              AND (
                    COALESCE(ca.tipo_concepto_asiento, '') <> 'Normal'
                 OR (ca.tipo_concepto IS NOT NULL
                     AND COALESCE(ca.tipo_concepto, '') <> COALESCE(ca.tipo_concepto_asiento, ''))
              )
            """,
            (id_ejercicio,),
        )
        rows = cur.fetchall()
        diferencias = [
            Diferencia(
                id_ejercicio=id_ejercicio,
                referencia_hallazgo="H37",
                detalle={
                    "id_concepto_asiento": to_int_or_none(r[0]),
                    "desc_concepto": str_or_default(r[1]),
                    "tipo_concepto_asiento": str_or_default(r[2]),
                    "tipo_concepto": str_or_default(r[3]),
                },
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


concepto_no_normal.check_id = "concepto_no_normal"
concepto_no_normal.titulo = "Concepto no normal en imputaciones"
concepto_no_normal.severidad = "medio"
