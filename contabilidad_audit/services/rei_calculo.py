"""Cálculo REI (ajuste por inflación) alineado con AdministraNET VB6.

Fuente: ``Cont_ProcesosC.frm`` — ``GeneraAsientoInflacion`` / ``generar_asiento_cont``.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import Decimal
from typing import Any, Optional

from core.utils.administranet_types import (
    str_or_default,
    to_date_or_none,
    to_decimal_or_none,
    to_int_or_none,
)

CONCEPTO_REI = 13
PARAMATRIZ_REI_CONTRAPARTIDA = 63
DESC_ASIENTO_REI = "Asiento por ajuste de inflación - REI "


def _as_date(value: Any) -> Optional[date]:
    """Normaliza a ``date`` para comparaciones (``to_date_or_none`` devuelve str)."""
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    s = to_date_or_none(value)
    if s is None:
        return None
    try:
        return datetime.strptime(s, "%Y-%m-%d").date()
    except ValueError:
        return None


@dataclass
class PeriodoIndice:
    fecdesde: date
    fechasta: date
    importe: Decimal


@dataclass
class ResultadoReiCuenta:
    id_pc: int
    cod_pc: str
    saldo_pc: str
    rei_teorico: Optional[Decimal]
    rei_registrado: Decimal
    computable: bool
    motivo_no_computable: Optional[str] = None
    detalle: dict[str, Any] = field(default_factory=dict)


@dataclass
class DesalineacionConfigRei:
    id_pc: Optional[int]
    cod_pc: Optional[str]
    tipo: str
    detalle: dict[str, Any] = field(default_factory=dict)


def fmt_fecha_usuario(fecha: Any) -> str:
    """Formato dd/MM/yyyy para mensajes al usuario."""
    d = _as_date(fecha)
    if d is None:
        return str_or_default(fecha, "-")
    return d.strftime("%d/%m/%Y")


def movimiento_firmado(debe: Any, haber: Any, saldo_pc: str) -> Decimal:
    """Movimiento según naturaleza de la cuenta (paso 2 de la fórmula REI)."""
    vdebe = to_decimal_or_none(debe) or Decimal("0")
    vhaber = to_decimal_or_none(haber) or Decimal("0")
    if saldo_pc == "Deudor":
        return vdebe - vhaber
    if saldo_pc == "Acreedor":
        return vhaber - vdebe
    return Decimal("0")


def cargar_periodos_indice(cur) -> list[PeriodoIndice]:
    """Índices de inflación vigentes (``anulado <> 'Si'``)."""
    cur.execute(
        """
        SELECT fecdesde_indiceinfla_periodo, fechasta_indiceinfla_periodo,
               importe_indiceinfla_periodo
        FROM cont_indiceinfla_periodo
        WHERE COALESCE(anulado, 'No') <> 'Si'
        ORDER BY fecdesde_indiceinfla_periodo
        """
    )
    periodos: list[PeriodoIndice] = []
    for row in cur.fetchall():
        if isinstance(row, dict):
            fecdesde = _as_date(row.get("fecdesde_indiceinfla_periodo"))
            fechasta = _as_date(row.get("fechasta_indiceinfla_periodo"))
            importe = to_decimal_or_none(row.get("importe_indiceinfla_periodo"))
        else:
            fecdesde = _as_date(row[0])
            fechasta = _as_date(row[1])
            importe = to_decimal_or_none(row[2])
        if fecdesde is None or fechasta is None or importe is None:
            continue
        periodos.append(PeriodoIndice(fecdesde=fecdesde, fechasta=fechasta, importe=importe))
    return periodos


def indice_cierre(periodos: list[PeriodoIndice], fechasta_ejercicio: date) -> Optional[Decimal]:
    """Coeficiente de cierre: índice cuya ``fechasta`` coincide con fin de ejercicio."""
    for p in periodos:
        if p.fechasta == fechasta_ejercicio:
            return p.importe
    return None


def indice_origen(
    periodos: list[PeriodoIndice], fecha_asiento: date
) -> tuple[Optional[Decimal], Optional[str]]:
    """Índice del mes del movimiento; devuelve (importe, motivo_error)."""
    coincidencias = [p for p in periodos if p.fecdesde <= fecha_asiento <= p.fechasta]
    if len(coincidencias) == 1:
        importe = coincidencias[0].importe
        if importe == 0:
            mes = fmt_fecha_usuario(fecha_asiento)
            return None, f"falta índice de origen para {mes} (importe cero)"
        return importe, None
    mes = fmt_fecha_usuario(fecha_asiento)
    return None, f"falta índice de origen para {mes}"


def rei_registrado_cuenta(cur, id_pc: int, id_ejercicio: int, saldo_pc: str) -> Decimal:
    """Suma firmada de renglones REI (concepto 13) no anulados."""
    cur.execute(
        """
        SELECT COALESCE(SUM(
            CASE %s
                WHEN 'Deudor'   THEN COALESCE(a.debe_asiento, 0) - COALESCE(a.haber_asiento, 0)
                WHEN 'Acreedor' THEN COALESCE(a.haber_asiento, 0) - COALESCE(a.debe_asiento, 0)
                ELSE 0
            END
        ), 0) AS total
        FROM cont_asiento a
        WHERE a.id_pc = %s AND a.id_ejercicio = %s
          AND a.id_concepto_asiento = %s
          AND COALESCE(a.anulado, 'No') <> 'Si'
        """,
        (saldo_pc, id_pc, id_ejercicio, CONCEPTO_REI),
    )
    row = cur.fetchone()
    if not row:
        return Decimal("0")
    if isinstance(row, dict):
        return to_decimal_or_none(row.get("total")) or Decimal("0")
    return to_decimal_or_none(row[0]) or Decimal("0")


def calcular_rei_teorico_cuenta(
    cur,
    *,
    id_pc: int,
    cod_pc: str,
    saldo_pc: str,
    id_ejercicio: int,
    ind_cierre: Decimal,
    periodos: list[PeriodoIndice],
) -> ResultadoReiCuenta:
    """Recalcula REI teórico acumulando **todos** los renglones base (fix H02)."""
    cur.execute(
        """
        SELECT a.fecha_asiento, a.debe_asiento, a.haber_asiento
        FROM cont_asiento a
        WHERE a.id_pc = %s AND a.id_ejercicio = %s
          AND COALESCE(a.id_concepto_asiento, 0) <> %s
        ORDER BY a.fecha_asiento, a.nro_asiento, a.codigo_movimiento
        """,
        (id_pc, id_ejercicio, CONCEPTO_REI),
    )
    renglones = cur.fetchall()
    total = Decimal("0")
    motivos: list[str] = []
    renglones_evaluados = 0

    for row in renglones:
        if isinstance(row, dict):
            fecha = _as_date(row.get("fecha_asiento"))
            debe = row.get("debe_asiento")
            haber = row.get("haber_asiento")
        else:
            fecha = _as_date(row[0])
            debe = row[1]
            haber = row[2]

        if fecha is None:
            motivos.append("fecha de asiento inválida en renglón base")
            break

        ind_orig, motivo = indice_origen(periodos, fecha)
        if ind_orig is None:
            if motivo and motivo not in motivos:
                motivos.append(motivo)
            break

        mov = movimiento_firmado(debe, haber, saldo_pc)
        subt = mov * (ind_cierre / ind_orig) - mov
        total += subt
        renglones_evaluados += 1

    rei_reg = rei_registrado_cuenta(cur, id_pc, id_ejercicio, saldo_pc)
    computable = len(motivos) == 0 and renglones_evaluados == len(renglones)
    motivo_final = "; ".join(motivos) if motivos else None

    return ResultadoReiCuenta(
        id_pc=id_pc,
        cod_pc=cod_pc,
        saldo_pc=saldo_pc,
        rei_teorico=total if computable else None,
        rei_registrado=rei_reg,
        computable=computable,
        motivo_no_computable=motivo_final,
        detalle={
            "renglones_base": len(renglones),
            "renglones_acumulados": renglones_evaluados,
            "ind_cierre": str(ind_cierre),
        },
    )


def fechasta_ejercicio(cur, id_ejercicio: int) -> Optional[date]:
    cur.execute(
        "SELECT fechasta_ejercicio FROM cont_ejercicio WHERE id_ejercicio = %s",
        (id_ejercicio,),
    )
    row = cur.fetchone()
    if not row:
        return None
    if isinstance(row, dict):
        return _as_date(row.get("fechasta_ejercicio"))
    return _as_date(row[0])


def id_pc_contrapartida_rei(cur) -> Optional[int]:
    cur.execute(
        "SELECT id_pc FROM cont_paramatriz WHERE id_paramatriz = %s",
        (PARAMATRIZ_REI_CONTRAPARTIDA,),
    )
    row = cur.fetchone()
    if not row:
        return None
    if isinstance(row, dict):
        return to_int_or_none(row.get("id_pc"))
    return to_int_or_none(row[0])


def cuentas_ajuste_inflacion(cur) -> list[tuple[int, str, str]]:
    cur.execute(
        """
        SELECT id_pc, cod_pc, saldo_pc
        FROM cont_pc
        WHERE COALESCE(ajuste_infla_pc, 'No') = 'Si'
        ORDER BY id_pc
        """
    )
    cuentas: list[tuple[int, str, str]] = []
    for row in cur.fetchall():
        if isinstance(row, dict):
            id_pc = to_int_or_none(row.get("id_pc"))
            cod_pc = str_or_default(row.get("cod_pc"))
            saldo_pc = str_or_default(row.get("saldo_pc"), "Deudor")
        else:
            id_pc = to_int_or_none(row[0])
            cod_pc = str_or_default(row[1])
            saldo_pc = str_or_default(row[2], "Deudor")
        if id_pc is not None:
            cuentas.append((id_pc, cod_pc, saldo_pc))
    return cuentas


def detectar_desalineacion_config(
    cur, id_ejercicio: int, id_pc_contra_esperado: Optional[int]
) -> list[DesalineacionConfigRei]:
    """Cuentas REI históricas vs config vigente (``ajuste_infla_pc`` / paramatriz 63)."""
    hallazgos: list[DesalineacionConfigRei] = []

    cur.execute(
        """
        SELECT DISTINCT a.id_pc, pc.cod_pc
        FROM cont_asiento a
        JOIN cont_pc pc ON pc.id_pc = a.id_pc
        WHERE a.id_ejercicio = %s
          AND a.id_concepto_asiento = %s
          AND COALESCE(a.anulado, 'No') <> 'Si'
          AND COALESCE(pc.ajuste_infla_pc, 'No') <> 'Si'
        ORDER BY a.id_pc
        """,
        (id_ejercicio, CONCEPTO_REI),
    )
    for row in cur.fetchall():
        if isinstance(row, dict):
            id_pc = to_int_or_none(row.get("id_pc"))
            cod_pc = str_or_default(row.get("cod_pc"))
        else:
            id_pc = to_int_or_none(row[0])
            cod_pc = str_or_default(row[1])
        hallazgos.append(
            DesalineacionConfigRei(
                id_pc=id_pc,
                cod_pc=cod_pc,
                tipo="cuenta_sin_ajuste_inflacion",
                detalle={
                    "mensaje": (
                        "REI registrado sobre cuenta sin ajuste_infla_pc='Si' en config vigente"
                    ),
                },
            )
        )

    if id_pc_contra_esperado is not None:
        cur.execute(
            """
            SELECT a.codigo_movimiento,
                   GROUP_CONCAT(DISTINCT a.id_pc ORDER BY a.id_pc) AS cuentas
            FROM cont_asiento a
            WHERE a.id_ejercicio = %s
              AND a.id_concepto_asiento = %s
              AND COALESCE(a.anulado, 'No') <> 'Si'
              AND COALESCE(a.codigo_movimiento, 0) <> 0
            GROUP BY a.codigo_movimiento
            HAVING SUM(CASE WHEN a.id_pc = %s THEN 1 ELSE 0 END) = 0
            ORDER BY a.codigo_movimiento
            """,
            (id_ejercicio, CONCEPTO_REI, id_pc_contra_esperado),
        )
        for row in cur.fetchall():
            if isinstance(row, dict):
                codmov = str_or_default(row.get("codigo_movimiento"))
                cuentas = str_or_default(row.get("cuentas"))
            else:
                codmov = str_or_default(row[0])
                cuentas = str_or_default(row[1])
            hallazgos.append(
                DesalineacionConfigRei(
                    id_pc=id_pc_contra_esperado,
                    cod_pc=None,
                    tipo="contrapartida_distinta",
                    detalle={
                        "mensaje": (
                            "REI registrado con contrapartida distinta a paramatriz 63 "
                            f"(id_pc esperado {id_pc_contra_esperado})"
                        ),
                        "codigo_movimiento": codmov,
                        "cuentas_asiento": cuentas,
                        "id_pc_contrapartida_esperado": id_pc_contra_esperado,
                    },
                )
            )

    return hallazgos


def evaluar_rei_ejercicio(cur, id_ejercicio: int) -> dict[str, Any]:
    """Evalúa REI teórico vs registrado y desalineaciones de config para un ejercicio."""
    periodos = cargar_periodos_indice(cur)
    fechasta = fechasta_ejercicio(cur, id_ejercicio)
    id_contra = id_pc_contrapartida_rei(cur)

    ind_cierre_val: Optional[Decimal] = None
    motivo_cierre: Optional[str] = None
    if fechasta is None:
        motivo_cierre = "ejercicio inexistente o sin fecha de cierre"
    else:
        ind_cierre_val = indice_cierre(periodos, fechasta)
        if ind_cierre_val is None:
            motivo_cierre = f"falta índice de cierre para {fmt_fecha_usuario(fechasta)}"

    cuentas_resultado: list[ResultadoReiCuenta] = []
    if ind_cierre_val is not None:
        for id_pc, cod_pc, saldo_pc in cuentas_ajuste_inflacion(cur):
            cuentas_resultado.append(
                calcular_rei_teorico_cuenta(
                    cur,
                    id_pc=id_pc,
                    cod_pc=cod_pc,
                    saldo_pc=saldo_pc,
                    id_ejercicio=id_ejercicio,
                    ind_cierre=ind_cierre_val,
                    periodos=periodos,
                )
            )
    else:
        for id_pc, cod_pc, saldo_pc in cuentas_ajuste_inflacion(cur):
            rei_reg = rei_registrado_cuenta(cur, id_pc, id_ejercicio, saldo_pc)
            cuentas_resultado.append(
                ResultadoReiCuenta(
                    id_pc=id_pc,
                    cod_pc=cod_pc,
                    saldo_pc=saldo_pc,
                    rei_teorico=None,
                    rei_registrado=rei_reg,
                    computable=False,
                    motivo_no_computable=motivo_cierre,
                    detalle={"fechasta_ejercicio": fmt_fecha_usuario(fechasta) if fechasta else None},
                )
            )

    desalineaciones = detectar_desalineacion_config(cur, id_ejercicio, id_contra)

    return {
        "id_ejercicio": id_ejercicio,
        "fechasta_ejercicio": fmt_fecha_usuario(fechasta) if fechasta else None,
        "ind_cierre": str(ind_cierre_val) if ind_cierre_val is not None else None,
        "motivo_ind_cierre": motivo_cierre,
        "id_pc_contrapartida": id_contra,
        "cuentas": cuentas_resultado,
        "desalineaciones": desalineaciones,
        "periodos_indice_cargados": len(periodos),
    }


def listar_codigos_movimiento_rei(cur, id_pc: int, id_ejercicio: int) -> list[str]:
    """Asientos REI vigentes identificados por concepto 13."""
    cur.execute(
        """
        SELECT DISTINCT codigo_movimiento
        FROM cont_asiento
        WHERE id_pc = %s AND id_ejercicio = %s
          AND id_concepto_asiento = %s
          AND COALESCE(anulado, 'No') <> 'Si'
          AND COALESCE(codigo_movimiento, 0) <> 0
          AND COALESCE(codigo_movimiento_anul, 0) = 0
        ORDER BY codigo_movimiento
        """,
        (id_pc, id_ejercicio, CONCEPTO_REI),
    )
    return [
        str_or_default(r["codigo_movimiento"] if isinstance(r, dict) else r[0])
        for r in cur.fetchall()
        if r
    ]
