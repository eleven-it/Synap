"""Checks de fechas y periodos contables."""
from __future__ import annotations

from core.utils.administranet_types import to_date_or_none, to_int_or_none, str_or_default

from contabilidad_audit.services.checks._sql import filtro_periodo_sql, id_ejercicio_filtro
from contabilidad_audit.services.resultados import (
    CorridaContexto,
    Diferencia,
    audit_result_error,
    construir_audit_result,
)


def _formatear_fecha_ui(fecha_iso: str | None) -> str:
    if not fecha_iso or len(fecha_iso) < 10:
        return "-"
    y, m, d = fecha_iso[:10].split("-")
    return f"{d}/{m}/{y}"


def fecha_fuera_de_periodo(base_empresa, filtros, politica, contexto: CorridaContexto):
    check_id = "fecha_fuera_de_periodo"
    titulo = "Fecha de asiento fuera del periodo"
    severidad = "medio"
    try:
        id_ejercicio = id_ejercicio_filtro(filtros)
        cur = contexto.cursor
        extra_periodo, params_periodo = filtro_periodo_sql(filtros, "a")
        cur.execute(
            f"""
            SELECT a.codigo_movimiento, a.nro_asiento, a.fecha_asiento,
                   a.id_periodo, p.fecdesde_periodo, p.fechasta_periodo
            FROM cont_asiento a
            LEFT JOIN cont_periodo p ON p.id_periodo = a.id_periodo
            WHERE a.id_ejercicio = %s
              {extra_periodo}
            """,
            [id_ejercicio, *params_periodo],
        )
        rows = cur.fetchall()
        diferencias: list[Diferencia] = []
        for row in rows:
            fecha = to_date_or_none(row[2])
            if fecha is None:
                diferencias.append(
                    Diferencia(
                        codigo_movimiento=str_or_default(row[0]),
                        nro_asiento=to_int_or_none(row[1]),
                        id_ejercicio=id_ejercicio,
                        id_periodo=to_int_or_none(row[3]),
                        referencia_hallazgo="H13",
                        detalle={"motivo": "fecha_asiento NULL o inválida"},
                    )
                )
                continue
            desde = to_date_or_none(row[4])
            hasta = to_date_or_none(row[5])
            if desde is None or hasta is None:
                continue
            if fecha < desde or fecha > hasta:
                diferencias.append(
                    Diferencia(
                        codigo_movimiento=str_or_default(row[0]),
                        nro_asiento=to_int_or_none(row[1]),
                        id_ejercicio=id_ejercicio,
                        id_periodo=to_int_or_none(row[3]),
                        referencia_hallazgo="H13",
                        detalle={
                            "fecha_asiento": _formatear_fecha_ui(fecha),
                            "fecdesde_periodo": _formatear_fecha_ui(desde),
                            "fechasta_periodo": _formatear_fecha_ui(hasta),
                        },
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


fecha_fuera_de_periodo.check_id = "fecha_fuera_de_periodo"
fecha_fuera_de_periodo.titulo = "Fecha de asiento fuera del periodo"
fecha_fuera_de_periodo.severidad = "medio"


def periodos_solapados(base_empresa, filtros, politica, contexto: CorridaContexto):
    check_id = "periodos_solapados"
    titulo = "Periodos contables solapados"
    severidad = "medio"
    try:
        id_ejercicio = id_ejercicio_filtro(filtros)
        cur = contexto.cursor
        cur.execute(
            """
            SELECT p1.id_periodo, p2.id_periodo,
                   p1.fecdesde_periodo, p1.fechasta_periodo,
                   p2.fecdesde_periodo, p2.fechasta_periodo
            FROM cont_periodo p1
            JOIN cont_periodo p2
              ON p1.id_ejercicio = p2.id_ejercicio
             AND p1.id_periodo < p2.id_periodo
            WHERE p1.id_ejercicio = %s
              AND p1.fecdesde_periodo IS NOT NULL
              AND p1.fechasta_periodo IS NOT NULL
              AND p2.fecdesde_periodo IS NOT NULL
              AND p2.fechasta_periodo IS NOT NULL
              AND p1.fecdesde_periodo <= p2.fechasta_periodo
              AND p2.fecdesde_periodo <= p1.fechasta_periodo
            """,
            (id_ejercicio,),
        )
        rows = cur.fetchall()
        diferencias = [
            Diferencia(
                id_ejercicio=id_ejercicio,
                id_periodo=to_int_or_none(r[0]),
                referencia_hallazgo="H28",
                detalle={
                    "id_periodo_conflicto": to_int_or_none(r[1]),
                    "periodo1": f"{_formatear_fecha_ui(to_date_or_none(r[2]))}-{_formatear_fecha_ui(to_date_or_none(r[3]))}",
                    "periodo2": f"{_formatear_fecha_ui(to_date_or_none(r[4]))}-{_formatear_fecha_ui(to_date_or_none(r[5]))}",
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


periodos_solapados.check_id = "periodos_solapados"
periodos_solapados.titulo = "Periodos contables solapados"
periodos_solapados.severidad = "medio"
