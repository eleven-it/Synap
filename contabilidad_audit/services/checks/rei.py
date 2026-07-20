"""Check de recálculo REI (solo lectura)."""
from __future__ import annotations

from decimal import Decimal

from contabilidad_audit.services.checks._sql import clasificar_delta, delta_decimal, id_ejercicio_filtro
from contabilidad_audit.services.rei_calculo import evaluar_rei_ejercicio
from contabilidad_audit.services.resultados import (
    CorridaContexto,
    Diferencia,
    audit_result_error,
    construir_audit_result,
)


def rei_recalculo(base_empresa, filtros, politica, contexto: CorridaContexto):
    """
    Recalcula REI teórico (fórmula VB6 corregida, fix H02) y lo compara contra
    asientos registrados (concepto 13). Reporta estado no computable y desalineación
    de config sin fabricar deltas espurios.
    """
    check_id = "rei_recalculo"
    titulo = "REI teórico vs registrado"
    severidad = "alto"
    try:
        id_ejercicio = id_ejercicio_filtro(filtros)
        evaluacion = evaluar_rei_ejercicio(contexto.cursor, id_ejercicio)
        diferencias: list[Diferencia] = []

        for cuenta in evaluacion["cuentas"]:
            if not cuenta.computable:
                diferencias.append(
                    Diferencia(
                        id_pc=cuenta.id_pc,
                        cod_pc=cuenta.cod_pc,
                        id_ejercicio=id_ejercicio,
                        valor_esperado=None,
                        valor_actual=cuenta.rei_registrado,
                        delta=None,
                        referencia_hallazgo="H02",
                        detalle={
                            "estado": "no_computable",
                            "motivo": cuenta.motivo_no_computable
                            or evaluacion.get("motivo_ind_cierre")
                            or "REI no computable",
                            **cuenta.detalle,
                        },
                    )
                )
                continue

            delta = delta_decimal(cuenta.rei_teorico, cuenta.rei_registrado)
            if delta is None:
                continue
            reportar, tipo_info = clasificar_delta(delta, politica)
            if reportar:
                diferencias.append(
                    Diferencia(
                        id_pc=cuenta.id_pc,
                        cod_pc=cuenta.cod_pc,
                        id_ejercicio=id_ejercicio,
                        valor_esperado=cuenta.rei_teorico,
                        valor_actual=cuenta.rei_registrado,
                        delta=delta,
                        referencia_hallazgo="H02",
                        detalle={
                            "estado": "delta_computable",
                            "tipo_informativo": tipo_info,
                            **cuenta.detalle,
                        },
                    )
                )

        for desal in evaluacion["desalineaciones"]:
            diferencias.append(
                Diferencia(
                    id_pc=desal.id_pc,
                    cod_pc=desal.cod_pc,
                    id_ejercicio=id_ejercicio,
                    valor_esperado=None,
                    valor_actual=None,
                    delta=None,
                    referencia_hallazgo="H44",
                    detalle={
                        "estado": "desalineacion_config",
                        "tipo": desal.tipo,
                        **desal.detalle,
                    },
                )
            )

        total_evaluado = len(evaluacion["cuentas"]) + len(evaluacion["desalineaciones"])
        return construir_audit_result(
            check_id=check_id,
            titulo=titulo,
            severidad=severidad,
            ok=len(diferencias) == 0,
            total_evaluado=total_evaluado,
            diferencias=diferencias,
            resumen={
                "id_ejercicio": id_ejercicio,
                "fechasta_ejercicio": evaluacion.get("fechasta_ejercicio"),
                "ind_cierre": evaluacion.get("ind_cierre"),
                "motivo_ind_cierre": evaluacion.get("motivo_ind_cierre"),
                "id_pc_contrapartida": evaluacion.get("id_pc_contrapartida"),
                "periodos_indice_cargados": evaluacion.get("periodos_indice_cargados"),
                "cuentas_ajuste": len(evaluacion["cuentas"]),
                "desalineaciones_config": len(evaluacion["desalineaciones"]),
            },
            contexto=contexto,
        )
    except Exception as exc:
        return audit_result_error(
            check_id=check_id, titulo=titulo, severidad=severidad, contexto=contexto, mensaje=str(exc)
        )


rei_recalculo.check_id = "rei_recalculo"
rei_recalculo.titulo = "REI teórico vs registrado"
rei_recalculo.severidad = "alto"
