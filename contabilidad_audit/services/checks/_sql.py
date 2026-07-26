"""SQL canónico y helpers numéricos para checks contables."""
from __future__ import annotations

from decimal import Decimal
from typing import Any, Optional

from core.utils.administranet_types import to_decimal_or_none, to_int_or_none

CENTAVO = Decimal("0.01")


def filtro_anulados_sql(politica: dict, alias: str = "a") -> str:
    """Fragmento WHERE según tratamiento_anulados."""
    if politica.get("tratamiento_anulados") == "incluir_neutralizado":
        return ""
    return f" AND COALESCE({alias}.anulado, 'No') <> 'Si' "


def sql_saldo_teorico(
    politica: dict,
    *,
    incluir_periodo: bool = True,
    filtros_extra: str = "",
) -> str:
    """Consulta canónica de saldo teórico desde cont_asiento (design §3.3)."""
    filtro_anul = filtro_anulados_sql(politica)
    cols_periodo = ", a.id_periodo" if incluir_periodo else ""
    group_periodo = ", a.id_periodo" if incluir_periodo else ""
    return f"""
        SELECT a.id_pc, a.id_ejercicio{cols_periodo},
               pc.cod_pc,
               pc.saldo_pc,
               CASE pc.saldo_pc
                    WHEN 'Deudor'   THEN SUM(COALESCE(a.debe_asiento, 0) - COALESCE(a.haber_asiento, 0))
                    WHEN 'Acreedor' THEN SUM(COALESCE(a.haber_asiento, 0) - COALESCE(a.debe_asiento, 0))
                    ELSE NULL
               END AS saldo_teorico
        FROM cont_asiento a
        JOIN cont_pc pc ON pc.id_pc = a.id_pc
        WHERE a.id_ejercicio = %s
          {filtro_anul}
          {filtros_extra}
        GROUP BY a.id_pc, a.id_ejercicio, pc.cod_pc, pc.saldo_pc{group_periodo}
    """


def umbral_reporte_delta(politica: dict) -> Decimal:
    """Umbral efectivo para reportar diferencia (decisión §5.1)."""
    tolerancia = to_decimal_or_none(politica.get("tolerancia_decimal")) or Decimal("0.005")
    if politica.get("politica_centavo") == "conservar_compensacion":
        return max(tolerancia, CENTAVO)
    return tolerancia


def clasificar_delta(
    delta: Decimal,
    politica: dict,
) -> tuple[bool, Optional[str]]:
    """
    Devuelve (reportar, tipo_informativo).
    tipo_informativo='compensacion_centavo' si aplica política conservar_compensacion.
    """
    tolerancia = to_decimal_or_none(politica.get("tolerancia_decimal")) or Decimal("0.005")
    abs_delta = abs(delta)
    if politica.get("politica_centavo") == "conservar_compensacion":
        if abs_delta <= max(tolerancia, CENTAVO):
            if abs_delta > tolerancia:
                return False, "compensacion_centavo"
            return False, None
        return True, None
    return abs_delta > tolerancia, None


def delta_decimal(valor_esperado: Any, valor_actual: Any) -> Optional[Decimal]:
    esperado = to_decimal_or_none(valor_esperado)
    actual = to_decimal_or_none(valor_actual)
    if esperado is None and actual is None:
        return Decimal("0")
    if esperado is None or actual is None:
        return None
    return esperado - actual


def filtro_fechas_sql(filtros: dict, alias: str = "a") -> tuple[str, list]:
    """Fragmento opcional por fecha_desde/fecha_hasta."""
    partes: list[str] = []
    params: list = []
    if filtros.get("fecha_desde"):
        partes.append(f" AND {alias}.fecha_asiento >= %s ")
        params.append(filtros["fecha_desde"])
    if filtros.get("fecha_hasta"):
        partes.append(f" AND {alias}.fecha_asiento <= %s ")
        params.append(filtros["fecha_hasta"])
    return "".join(partes), params


def filtro_periodo_sql(filtros: dict, alias: str = "a") -> tuple[str, list]:
    if filtros.get("id_periodo") is None:
        return "", []
    return f" AND {alias}.id_periodo = %s ", [filtros["id_periodo"]]


def cod_pc_coincide_prefijo(cod_pc: str, prefijos: list[str]) -> bool:
    cod = (cod_pc or "").strip()
    for pref in prefijos:
        p = str(pref).strip()
        if not p:
            continue
        if p.endswith("%"):
            if cod.startswith(p[:-1]):
                return True
        elif cod.startswith(p):
            return True
    return False


def id_ejercicio_filtro(filtros: dict) -> int:
    return int(filtros["id_ejercicio"])


def join_cont_ejercicio_por_fecha(alias: str, ej_alias: str = "ej") -> str:
    """JOIN ``cont_ejercicio`` acotando ``{alias}.Fecha`` al rango del ejercicio filtrado."""
    return f"""
            JOIN cont_ejercicio {ej_alias} ON {ej_alias}.id_ejercicio = %s
             AND {alias}.Fecha BETWEEN {ej_alias}.fecdesde_ejercicio AND {ej_alias}.fechasta_ejercicio
            """


def filtro_periodo_comprobante_por_fecha_sql(
    filtros: dict | None,
    alias: str,
) -> tuple[str, list]:
    """Fragmento ``AND EXISTS (cont_periodo …)`` opcional por ``Fecha`` del comprobante."""
    if not filtros:
        return "", []
    id_periodo = to_int_or_none(filtros.get("id_periodo"))
    if id_periodo is None:
        return "", []
    return (
        f"""
              AND EXISTS (
                  SELECT 1 FROM cont_periodo pe
                  WHERE pe.id_periodo = %s
                    AND {alias}.Fecha BETWEEN pe.fecdesde_periodo AND pe.fechasta_periodo
              )
        """,
        [id_periodo],
    )


def filtro_periodo_dentro_exists_por_fecha_sql(
    filtros: dict | None,
    alias: str,
) -> tuple[str, list]:
    """Condición ``AND EXISTS (cont_periodo …)`` para usar dentro de subconsultas EXISTS."""
    if not filtros:
        return "", []
    id_periodo = to_int_or_none(filtros.get("id_periodo"))
    if id_periodo is None:
        return "", []
    return (
        f"""
                    AND EXISTS (
                        SELECT 1 FROM cont_periodo pe
                        WHERE pe.id_periodo = %s
                          AND {alias}.Fecha BETWEEN pe.fecdesde_periodo AND pe.fechasta_periodo
                    )
        """,
        [id_periodo],
    )
