"""Checks de saldos derivados vs diario."""
from __future__ import annotations

from decimal import Decimal

from core.utils.administranet_types import to_decimal_or_none, to_int_or_none, str_or_default

from contabilidad_audit.services.checks._sql import (
    clasificar_delta,
    delta_decimal,
    filtro_fechas_sql,
    filtro_periodo_sql,
    id_ejercicio_filtro,
    sql_saldo_teorico,
)
from contabilidad_audit.services.resultados import (
    CorridaContexto,
    Diferencia,
    audit_result_error,
    construir_audit_result,
)

CHECK_SALDO_EJERCICIO = "saldo_ejercicio_vs_diario"
CHECK_SALDO_PERIODO = "saldo_periodo_vs_diario"
CHECK_CUENTAS_SIN_FILA = "cuentas_sin_fila_saldo"


def saldo_ejercicio_vs_diario(
    base_empresa: str,
    filtros: dict,
    politica: dict,
    contexto: CorridaContexto,
):
    check_id = CHECK_SALDO_EJERCICIO
    titulo = "Saldo ejercicio vs diario"
    severidad = "critico"
    try:
        id_ejercicio = id_ejercicio_filtro(filtros)
        cur = contexto.cursor
        extra_fecha, params_fecha = filtro_fechas_sql(filtros)
        extra_periodo, params_periodo = filtro_periodo_sql(filtros)
        sql = sql_saldo_teorico(
            politica,
            incluir_periodo=False,
            filtros_extra=extra_fecha + extra_periodo,
        )
        cur.execute(sql, [id_ejercicio, *params_fecha, *params_periodo])
        teoricos: dict[int, dict] = {}
        for row in cur.fetchall():
            id_pc = to_int_or_none(row[0])
            if id_pc is None:
                continue
            cod_pc = str_or_default(row[2])
            saldo_pc = str_or_default(row[3], "")
            saldo_teorico = row[4]
            if saldo_pc not in ("Deudor", "Acreedor") or saldo_teorico is None:
                teoricos[id_pc] = {"saldo_pc": saldo_pc, "cod_pc": cod_pc, "saldo": None}
            else:
                acum = teoricos.get(id_pc, {}).get("saldo") or Decimal("0")
                acum += to_decimal_or_none(saldo_teorico) or Decimal("0")
                teoricos[id_pc] = {"saldo_pc": saldo_pc, "cod_pc": cod_pc, "saldo": acum}

        cur.execute(
            """
            SELECT id_pc, saldo_ejercicio_cta
            FROM cont_ejercicio_saldo_cta
            WHERE id_ejercicio = %s
            """,
            (id_ejercicio,),
        )
        derivados = {
            to_int_or_none(r[0]): to_decimal_or_none(r[1])
            for r in cur.fetchall()
            if to_int_or_none(r[0]) is not None
        }

        diferencias: list[Diferencia] = []
        compensaciones: list[dict] = []
        evaluados = set(teoricos.keys()) | set(derivados.keys())
        for id_pc in evaluados:
            info = teoricos.get(id_pc, {})
            saldo_pc = info.get("saldo_pc", "")
            cod_pc = info.get("cod_pc")
            if saldo_pc not in ("Deudor", "Acreedor") and id_pc in teoricos:
                diferencias.append(
                    Diferencia(
                        id_pc=id_pc,
                        cod_pc=cod_pc,
                        id_ejercicio=id_ejercicio,
                        referencia_hallazgo="H04",
                        detalle={"motivo": "saldo_pc NULL o desconocido"},
                    )
                )
                continue
            teorico = info.get("saldo")
            actual = derivados.get(id_pc)
            delta = delta_decimal(teorico, actual)
            if delta is None:
                continue
            reportar, tipo = clasificar_delta(delta, politica)
            if not reportar:
                if tipo == "compensacion_centavo":
                    compensaciones.append({"id_pc": id_pc, "cod_pc": cod_pc, "delta": str(delta)})
                continue
            diferencias.append(
                Diferencia(
                    id_pc=id_pc,
                    cod_pc=cod_pc,
                    id_ejercicio=id_ejercicio,
                    valor_esperado=teorico,
                    valor_actual=actual,
                    delta=delta,
                    referencia_hallazgo="H04",
                )
            )

        return construir_audit_result(
            check_id=check_id,
            titulo=titulo,
            severidad=severidad,
            ok=len(diferencias) == 0,
            total_evaluado=len(evaluados),
            diferencias=diferencias,
            resumen={"id_ejercicio": id_ejercicio},
            contexto=contexto,
            compensaciones_centavo=compensaciones or None,
        )
    except Exception as exc:
        return audit_result_error(
            check_id=check_id,
            titulo=titulo,
            severidad=severidad,
            contexto=contexto,
            mensaje=str(exc),
        )


saldo_ejercicio_vs_diario.check_id = CHECK_SALDO_EJERCICIO
saldo_ejercicio_vs_diario.titulo = "Saldo ejercicio vs diario"
saldo_ejercicio_vs_diario.severidad = "critico"


def saldo_periodo_vs_diario(
    base_empresa: str,
    filtros: dict,
    politica: dict,
    contexto: CorridaContexto,
):
    check_id = CHECK_SALDO_PERIODO
    titulo = "Saldo periodo vs diario"
    severidad = "critico"
    try:
        id_ejercicio = id_ejercicio_filtro(filtros)
        cur = contexto.cursor
        extra_fecha, params_fecha = filtro_fechas_sql(filtros)
        extra_periodo, params_periodo = filtro_periodo_sql(filtros)
        sql = sql_saldo_teorico(
            politica,
            incluir_periodo=True,
            filtros_extra=extra_fecha + extra_periodo,
        )
        cur.execute(sql, [id_ejercicio, *params_fecha, *params_periodo])
        teoricos: dict[tuple, dict] = {}
        for row in cur.fetchall():
            id_pc = to_int_or_none(row[0])
            id_periodo = to_int_or_none(row[2])
            cod_pc = str_or_default(row[3])
            saldo_pc = str_or_default(row[4], "")
            saldo_teorico = row[5]
            clave = (id_pc, id_periodo)
            if saldo_pc not in ("Deudor", "Acreedor") or saldo_teorico is None:
                teoricos[clave] = {"saldo_pc": saldo_pc, "cod_pc": cod_pc, "saldo": None}
            else:
                teoricos[clave] = {
                    "saldo_pc": saldo_pc,
                    "cod_pc": cod_pc,
                    "saldo": to_decimal_or_none(saldo_teorico),
                }

        cur.execute(
            """
            SELECT id_pc, id_periodo, saldo_periodo_cta
            FROM cont_periodo_saldo_cta
            WHERE id_ejercicio = %s
            """,
            (id_ejercicio,),
        )
        derivados = {}
        for r in cur.fetchall():
            clave = (to_int_or_none(r[0]), to_int_or_none(r[1]))
            derivados[clave] = to_decimal_or_none(r[2])

        diferencias: list[Diferencia] = []
        compensaciones: list[dict] = []
        evaluados = set(teoricos.keys()) | set(derivados.keys())
        for clave in evaluados:
            id_pc, id_periodo = clave
            info = teoricos.get(clave, {})
            saldo_pc = info.get("saldo_pc", "")
            if saldo_pc not in ("Deudor", "Acreedor") and clave in teoricos:
                diferencias.append(
                    Diferencia(
                        id_pc=id_pc,
                        id_periodo=id_periodo,
                        id_ejercicio=id_ejercicio,
                        referencia_hallazgo="H04",
                        detalle={"motivo": "saldo_pc NULL o desconocido"},
                    )
                )
                continue
            teorico = info.get("saldo")
            actual = derivados.get(clave)
            delta = delta_decimal(teorico, actual)
            if delta is None:
                continue
            reportar, tipo = clasificar_delta(delta, politica)
            if not reportar:
                if tipo == "compensacion_centavo":
                    compensaciones.append({"id_pc": id_pc, "id_periodo": id_periodo, "delta": str(delta)})
                continue
            diferencias.append(
                Diferencia(
                    id_pc=id_pc,
                    cod_pc=info.get("cod_pc"),
                    id_ejercicio=id_ejercicio,
                    id_periodo=id_periodo,
                    valor_esperado=teorico,
                    valor_actual=actual,
                    delta=delta,
                    referencia_hallazgo="H03",
                )
            )

        return construir_audit_result(
            check_id=check_id,
            titulo=titulo,
            severidad=severidad,
            ok=len(diferencias) == 0,
            total_evaluado=len(evaluados),
            diferencias=diferencias,
            resumen={"id_ejercicio": id_ejercicio},
            contexto=contexto,
            compensaciones_centavo=compensaciones or None,
        )
    except Exception as exc:
        return audit_result_error(
            check_id=check_id,
            titulo=titulo,
            severidad=severidad,
            contexto=contexto,
            mensaje=str(exc),
        )


saldo_periodo_vs_diario.check_id = CHECK_SALDO_PERIODO
saldo_periodo_vs_diario.titulo = "Saldo periodo vs diario"
saldo_periodo_vs_diario.severidad = "critico"


def cuentas_sin_fila_saldo(
    base_empresa: str,
    filtros: dict,
    politica: dict,
    contexto: CorridaContexto,
):
    check_id = CHECK_CUENTAS_SIN_FILA
    titulo = "Cuentas imputables sin fila de saldo"
    severidad = "alto"
    try:
        id_ejercicio = id_ejercicio_filtro(filtros)
        cur = contexto.cursor
        filtro_anul = ""
        if politica.get("tratamiento_anulados") != "incluir_neutralizado":
            filtro_anul = " AND COALESCE(a.anulado, 'No') <> 'Si' "
        extra_periodo, params_periodo = filtro_periodo_sql(filtros, "a")
        cur.execute(
            f"""
            SELECT DISTINCT a.id_pc, pc.cod_pc, a.id_periodo
            FROM cont_asiento a
            JOIN cont_pc pc ON pc.id_pc = a.id_pc
            WHERE a.id_ejercicio = %s
              AND COALESCE(pc.imp_cont_pc, '') = 'Imputable'
              {filtro_anul}
              {extra_periodo}
            """,
            [id_ejercicio, *params_periodo],
        )
        movimientos = cur.fetchall()

        cur.execute(
            "SELECT id_pc FROM cont_ejercicio_saldo_cta WHERE id_ejercicio = %s",
            (id_ejercicio,),
        )
        ejercicio_saldos = {to_int_or_none(r[0]) for r in cur.fetchall()}

        cur.execute(
            "SELECT id_pc, id_periodo FROM cont_periodo_saldo_cta WHERE id_ejercicio = %s",
            (id_ejercicio,),
        )
        periodo_saldos = {
            (to_int_or_none(r[0]), to_int_or_none(r[1])) for r in cur.fetchall()
        }

        diferencias: list[Diferencia] = []
        vistos: set[tuple] = set()
        for row in movimientos:
            id_pc = to_int_or_none(row[0])
            cod_pc = str_or_default(row[1])
            id_periodo = to_int_or_none(row[2])
            if id_pc is None:
                continue
            if id_pc not in ejercicio_saldos:
                clave = ("ej", id_pc)
                if clave not in vistos:
                    vistos.add(clave)
                    diferencias.append(
                        Diferencia(
                            id_pc=id_pc,
                            cod_pc=cod_pc,
                            id_ejercicio=id_ejercicio,
                            referencia_hallazgo="H34",
                            detalle={"tabla": "cont_ejercicio_saldo_cta"},
                        )
                    )
            if id_periodo is not None and (id_pc, id_periodo) not in periodo_saldos:
                clave = ("per", id_pc, id_periodo)
                if clave not in vistos:
                    vistos.add(clave)
                    diferencias.append(
                        Diferencia(
                            id_pc=id_pc,
                            cod_pc=cod_pc,
                            id_ejercicio=id_ejercicio,
                            id_periodo=id_periodo,
                            referencia_hallazgo="H17",
                            detalle={"tabla": "cont_periodo_saldo_cta"},
                        )
                    )

        return construir_audit_result(
            check_id=check_id,
            titulo=titulo,
            severidad=severidad,
            ok=len(diferencias) == 0,
            total_evaluado=len(movimientos),
            diferencias=diferencias,
            resumen={"id_ejercicio": id_ejercicio},
            contexto=contexto,
        )
    except Exception as exc:
        return audit_result_error(
            check_id=check_id,
            titulo=titulo,
            severidad=severidad,
            contexto=contexto,
            mensaje=str(exc),
        )


cuentas_sin_fila_saldo.check_id = CHECK_CUENTAS_SIN_FILA
cuentas_sin_fila_saldo.titulo = "Cuentas imputables sin fila de saldo"
cuentas_sin_fila_saldo.severidad = "alto"
