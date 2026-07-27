"""Motor de recálculo contable legacy (dry-run Fase 2 / apply Fase 3).

Fase 2: ``dry_run`` es 100 % SELECT sobre MySQL legacy; persiste el plan en
PostgreSQL (``PlanCorreccion``). Fase 3: ``apply`` / ``rollback_lote`` escriben
en legacy con permiso reforzado (cualquier entorno, incluido development).
"""
from __future__ import annotations

import hashlib
import json
import logging
import uuid
from collections import defaultdict
from datetime import timedelta
from collections.abc import Callable, Iterator
from decimal import Decimal, ROUND_HALF_UP
from typing import Any, Optional

import MySQLdb.cursors

from core.mysql_pool import get_mysql_pool
from core.utils.administranet_types import (
    str_or_default,
    to_date_or_none,
    to_decimal_or_none,
    to_int_or_none,
)
from django.utils import timezone

from contabilidad_audit.models import AprobacionREI, PlanCorreccion
from contabilidad_audit.services.politicas import calcular_config_hash, resolver_politica
from contabilidad_audit.services.rei_calculo import (
    CONCEPTO_REI,
    DESC_ASIENTO_REI,
    PARAMATRIZ_REI_CONTRAPARTIDA,
    evaluar_rei_ejercicio,
    listar_codigos_movimiento_rei,
    rei_registrado_cuenta,
)

logger = logging.getLogger(__name__)
PLAN_TTL_MIN = 30
PERMISO_CORREGIR = "contabilidad.auditoria.corregir"
TABLAS_BACKUP_PERMITIDAS = frozenset(
    {
        "cont_asiento",
        "cont_ejercicio_saldo_cta",
        "cont_periodo_saldo_cta",
        "cuentaproveedor",
        "cuentacliente",
    }
)
CHECKS_EXCLUIDOS_AUTO_APPLY = frozenset(
    {
        "cierre_resultado_no_cero",
        "asiento_compra_pago_desbalanceado_saldo_null",
        "asiento_balanceado",
        "rei_recalculo",
    }
)

TIPOS_FACTURA = ("FA", "FC")
TIPOS_REGENERABLES = ("FA", "FC", "OP")
TIPOS_FACTURA_VENTA = ("FA", "FB", "FC", "FE", "FM")
TIPOS_REGENERABLES_VENTA = TIPOS_FACTURA_VENTA + ("REC",)
CONCEPTO = {"FA": 3, "FC": 3, "OP": 7}
CONCEPTO_VENTA = {
    "FA": 1,
    "FB": 1,
    "FC": 1,
    "FE": 1,
    "FM": 1,
    "REC": 5,
}
DESC_CONCEPTO = {3: "Compra", 7: "Pago"}
DESC_CONCEPTO_VENTA = {1: "Venta", 5: "Cobranza"}
REDONDEO_PC = 300
UMBRAL_REDONDEO = Decimal("1.00")
MARCA_REGEN = "REGEN auditoria (bug factura/OP sin asiento)"
MARCA_REGEN_VENTA = "REGEN auditoria (bug factura/REC sin asiento)"
MARCA_ANUL_REGEN = "REGEN auditoria (anulacion incompleta)"

CHECK_REGENERACION = "comprobante_compra_pago_sin_asiento"
CHECK_REGENERACION_VENTA = "comprobante_venta_cobranza_sin_asiento"
CHECK_ANULACION = "integridad_anulacion_compra_pago"
CHECK_CONCEPTO_ANUL = "concepto_anulacion_incoherente"
CHECK_FILAS_SALDO = "cuentas_sin_fila_saldo"
CHECK_SALDOS = "saldo_ejercicio_vs_diario"
CHECK_SALDOS_PERIODO = "saldo_periodo_vs_diario"
CHECK_REI = "rei_recalculo"
CHECKS_INCLUIDOS = [
    CHECK_REGENERACION,
    CHECK_REGENERACION_VENTA,
    CHECK_ANULACION,
    CHECK_CONCEPTO_ANUL,
    CHECK_FILAS_SALDO,
    CHECK_SALDOS,
    CHECK_SALDOS_PERIODO,
]
CHECKS_SALDOS = frozenset({CHECK_FILAS_SALDO, CHECK_SALDOS, CHECK_SALDOS_PERIODO})
CHECKS_MOTOR_DRY_RUN = frozenset(CHECKS_INCLUIDOS) | {CHECK_REI}
CHECKS_REGENERACION_ASIENTO = frozenset({CHECK_REGENERACION, CHECK_REGENERACION_VENTA})
CONCEPTO_ANUL = {"FA": 4, "FC": 4, "OP": 8}
DESC_CONCEPTO_ANUL = {4: "Anulación-Compra", 8: "Anulación-Pago"}
MARCA_REI_REGEN = "REI auditoria (recalculo aprobado)"

Q2 = Decimal("0.01")


def _d(valor: Any) -> Decimal:
    dec = to_decimal_or_none(valor)
    return dec if dec is not None else Decimal("0")


def _r2(valor: Any) -> Decimal:
    return _d(valor).quantize(Q2, rounding=ROUND_HALF_UP)


def _incluir_anulado(tratamiento_anulados: str) -> bool:
    return tratamiento_anulados == "incluir_neutralizado"


# Conta_Info / conta_libro_mayor.rpt lee cont_asiento.saldo_asiento sin filtrar
# anulado. Regla canónica Synap (pie, corrido, checks): incluir_neutralizado
# (contra-asiento + original se netean). Alias explícito para el corrido LM.
TRATAMIENTO_ANULADOS_LIBRO_MAYOR = "incluir_neutralizado"


def _saldo_teorico_cuenta(
    dict_cur,
    id_pc: int,
    id_ejercicio: int,
    *,
    tratamiento_anulados: str = "incluir_neutralizado",
    id_periodo: int | None = None,
) -> Decimal:
    """Devuelve la suma firmada de una cuenta, con precisión plena hasta el final."""
    filtro_anulado = ""
    if not _incluir_anulado(tratamiento_anulados):
        filtro_anulado = " AND COALESCE(a.anulado, 'No') <> 'Si'"
    filtro_periodo = ""
    params: list[Any] = [id_ejercicio, id_pc]
    if id_periodo is not None:
        filtro_periodo = " AND a.id_periodo = %s"
        params.append(id_periodo)

    dict_cur.execute(
        f"""
        SELECT
            pc.saldo_pc,
            SUM(
                CASE pc.saldo_pc
                    WHEN 'Deudor' THEN COALESCE(a.debe_asiento, 0) - COALESCE(a.haber_asiento, 0)
                    WHEN 'Acreedor' THEN COALESCE(a.haber_asiento, 0) - COALESCE(a.debe_asiento, 0)
                    ELSE 0
                END
            ) AS saldo_teorico
        FROM cont_asiento a
        JOIN cont_pc pc ON pc.id_pc = a.id_pc
        WHERE a.id_ejercicio = %s AND a.id_pc = %s
          {filtro_periodo}
          {filtro_anulado}
        GROUP BY a.id_pc, a.id_ejercicio, pc.saldo_pc
        """,
        params,
    )
    fila = dict_cur.fetchone() or {}
    return _r2(fila.get("saldo_teorico"))


def _guardar_saldo_ejercicio(
    cur,
    dict_cur,
    id_pc: int,
    id_ejercicio: int,
    saldo: Decimal,
) -> None:
    dict_cur.execute(
        """SELECT 1 FROM cont_ejercicio_saldo_cta
           WHERE id_pc=%s AND id_ejercicio=%s LIMIT 1""",
        (id_pc, id_ejercicio),
    )
    if dict_cur.fetchone():
        cur.execute(
            """UPDATE cont_ejercicio_saldo_cta SET saldo_ejercicio_cta=%s
               WHERE id_pc=%s AND id_ejercicio=%s""",
            (str(_r2(saldo)), id_pc, id_ejercicio),
        )
    else:
        cur.execute(
            """INSERT INTO cont_ejercicio_saldo_cta
               (id_pc, id_ejercicio, saldo_ejercicio_cta) VALUES (%s,%s,%s)""",
            (id_pc, id_ejercicio, str(_r2(saldo))),
        )


def _guardar_saldo_periodo(
    cur,
    dict_cur,
    id_pc: int,
    id_ejercicio: int,
    id_periodo: int,
    saldo: Decimal,
) -> None:
    dict_cur.execute(
        """SELECT 1 FROM cont_periodo_saldo_cta
           WHERE id_pc=%s AND id_ejercicio=%s AND id_periodo=%s LIMIT 1""",
        (id_pc, id_ejercicio, id_periodo),
    )
    if dict_cur.fetchone():
        cur.execute(
            """UPDATE cont_periodo_saldo_cta SET saldo_periodo_cta=%s
               WHERE id_pc=%s AND id_ejercicio=%s AND id_periodo=%s""",
            (str(_r2(saldo)), id_pc, id_ejercicio, id_periodo),
        )
    else:
        cur.execute(
            """INSERT INTO cont_periodo_saldo_cta
               (id_pc, id_ejercicio, id_periodo, saldo_periodo_cta) VALUES (%s,%s,%s,%s)""",
            (id_pc, id_ejercicio, id_periodo, str(_r2(saldo))),
        )


_TMP_LM_SALDOS = "tmp_lm_saldos"
_CHUNK_STAGING_LM = 1000


def _acumular_saldos_corridos(
    filas: list[dict],
    naturaleza: str,
) -> list[tuple[Any, Decimal]]:
    """Acumula saldo corrido Libro Mayor por renglón (orden ya aplicado en ``filas``)."""
    saldo = Decimal("0")
    resultado: list[tuple[Any, Decimal]] = []
    for fila in filas:
        debe = _d(fila.get("debe_asiento"))
        haber = _d(fila.get("haber_asiento"))
        saldo += haber - debe if naturaleza == "Acreedor" else debe - haber
        resultado.append((fila.get("id_asiento"), _r2(saldo)))
    return resultado


def _acumular_saldos_corridos_multicuenta(
    filas: list[dict],
) -> list[tuple[Any, Decimal]]:
    """Acumula corrido para varias cuentas/ejercicios (filas ordenadas por cuenta y fecha)."""
    saldo_por_clave: dict[tuple[int | None, int | None], Decimal] = {}
    resultado: list[tuple[Any, Decimal]] = []
    for fila in filas:
        clave = (to_int_or_none(fila.get("id_ejercicio")), to_int_or_none(fila.get("id_pc")))
        naturaleza = str_or_default(fila.get("saldo_pc"), "Deudor")
        saldo = saldo_por_clave.get(clave, Decimal("0"))
        debe = _d(fila.get("debe_asiento"))
        haber = _d(fila.get("haber_asiento"))
        saldo += haber - debe if naturaleza == "Acreedor" else debe - haber
        saldo_por_clave[clave] = saldo
        resultado.append((fila.get("id_asiento"), _r2(saldo)))
    return resultado


def _crear_temp_lm_saldos(cur) -> None:
    ddl_memory = f"""
        CREATE TEMPORARY TABLE {_TMP_LM_SALDOS} (
            id_asiento DOUBLE NOT NULL PRIMARY KEY,
            saldo_asiento DECIMAL(18,2) NOT NULL
        ) ENGINE=Memory
    """
    try:
        cur.execute(ddl_memory)
    except Exception:
        cur.execute(
            f"""
            CREATE TEMPORARY TABLE {_TMP_LM_SALDOS} (
                id_asiento DOUBLE NOT NULL PRIMARY KEY,
                saldo_asiento DECIMAL(18,2) NOT NULL
            ) ENGINE=InnoDB
            """
        )


def _insertar_staging_lm_saldos(cur, registros: list[tuple[Any, Decimal]]) -> None:
    for offset in range(0, len(registros), _CHUNK_STAGING_LM):
        chunk = registros[offset : offset + _CHUNK_STAGING_LM]
        placeholders = ",".join(["(%s,%s)"] * len(chunk))
        params: list[Any] = []
        for id_asiento, saldo in chunk:
            params.extend([id_asiento, str(saldo)])
        cur.execute(
            f"INSERT INTO {_TMP_LM_SALDOS} (id_asiento, saldo_asiento) VALUES {placeholders}",
            params,
        )


def _saldos_teoricos_agregados(
    dict_cur,
    id_ejercicios: list[int],
    *,
    tratamiento_anulados: str = "incluir_neutralizado",
    id_periodo: int | None = None,
) -> list[dict]:
    """Suma firmada por cuenta (y opcionalmente periodo) en una sola consulta."""
    if not id_ejercicios:
        return []
    placeholders = ",".join(["%s"] * len(id_ejercicios))
    filtro_anulado = ""
    if not _incluir_anulado(tratamiento_anulados):
        filtro_anulado = " AND COALESCE(a.anulado, 'No') <> 'Si'"
    filtro_periodo = ""
    params: list[Any] = list(id_ejercicios)
    group_periodo = ""
    select_periodo = ""
    if id_periodo is not None:
        filtro_periodo = " AND a.id_periodo = %s"
        params.append(id_periodo)
        group_periodo = ", a.id_periodo"
        select_periodo = ", a.id_periodo"
    dict_cur.execute(
        f"""
        SELECT
            a.id_pc,
            a.id_ejercicio{select_periodo},
            pc.saldo_pc,
            SUM(
                CASE pc.saldo_pc
                    WHEN 'Deudor' THEN COALESCE(a.debe_asiento, 0) - COALESCE(a.haber_asiento, 0)
                    WHEN 'Acreedor' THEN COALESCE(a.haber_asiento, 0) - COALESCE(a.debe_asiento, 0)
                    ELSE 0
                END
            ) AS saldo_teorico
        FROM cont_asiento a
        JOIN cont_pc pc ON pc.id_pc = a.id_pc
        WHERE a.id_ejercicio IN ({placeholders})
          AND a.id_pc IS NOT NULL
          {filtro_periodo}
          {filtro_anulado}
        GROUP BY a.id_pc, a.id_ejercicio{group_periodo}, pc.saldo_pc
        ORDER BY a.id_ejercicio, a.id_pc{group_periodo}
        """,
        params,
    )
    return list(dict_cur.fetchall() or [])


def _saldos_teoricos_periodos_agregados(
    dict_cur,
    id_ejercicios: list[int],
    *,
    tratamiento_anulados: str = "incluir_neutralizado",
) -> list[dict]:
    """Suma firmada por cuenta y periodo en una sola consulta."""
    if not id_ejercicios:
        return []
    placeholders = ",".join(["%s"] * len(id_ejercicios))
    filtro_anulado = ""
    if not _incluir_anulado(tratamiento_anulados):
        filtro_anulado = " AND COALESCE(a.anulado, 'No') <> 'Si'"
    dict_cur.execute(
        f"""
        SELECT
            a.id_pc,
            a.id_ejercicio,
            a.id_periodo,
            pc.saldo_pc,
            SUM(
                CASE pc.saldo_pc
                    WHEN 'Deudor' THEN COALESCE(a.debe_asiento, 0) - COALESCE(a.haber_asiento, 0)
                    WHEN 'Acreedor' THEN COALESCE(a.haber_asiento, 0) - COALESCE(a.debe_asiento, 0)
                    ELSE 0
                END
            ) AS saldo_teorico
        FROM cont_asiento a
        JOIN cont_pc pc ON pc.id_pc = a.id_pc
        WHERE a.id_ejercicio IN ({placeholders})
          AND a.id_pc IS NOT NULL
          AND a.id_periodo IS NOT NULL
          {filtro_anulado}
        GROUP BY a.id_pc, a.id_ejercicio, a.id_periodo, pc.saldo_pc
        ORDER BY a.id_ejercicio, a.id_pc, a.id_periodo
        """,
        list(id_ejercicios),
    )
    return list(dict_cur.fetchall() or [])


def _recalcular_saldo_asiento_setbased(
    cur,
    dict_cur,
    *,
    id_ejercicios: list[int],
    id_pcs: list[int] | None = None,
) -> int:
    """Recalcula ``cont_asiento.saldo_asiento`` con staging temporal + UPDATE JOIN."""
    if not id_ejercicios:
        return 0

    placeholders_ej = ",".join(["%s"] * len(id_ejercicios))
    params: list[Any] = list(id_ejercicios)
    filtro_pc = ""
    if id_pcs:
        placeholders_pc = ",".join(["%s"] * len(id_pcs))
        filtro_pc = f" AND a.id_pc IN ({placeholders_pc})"
        params.extend(id_pcs)

    dict_cur.execute(
        f"""
        SELECT
            a.id_asiento,
            a.id_pc,
            a.id_ejercicio,
            a.debe_asiento,
            a.haber_asiento,
            pc.saldo_pc
        FROM cont_asiento a
        JOIN cont_pc pc ON pc.id_pc = a.id_pc
        WHERE a.id_ejercicio IN ({placeholders_ej})
          AND a.id_pc IS NOT NULL
          {filtro_pc}
        ORDER BY a.id_ejercicio, a.id_pc, a.fecha_asiento, a.nro_asiento, a.id_asiento
        """,
        params,
    )
    filas = dict_cur.fetchall() or []
    if not filas:
        return 0

    registros = _acumular_saldos_corridos_multicuenta(filas)
    cur.execute(f"DROP TEMPORARY TABLE IF EXISTS {_TMP_LM_SALDOS}")
    _crear_temp_lm_saldos(cur)
    try:
        _insertar_staging_lm_saldos(cur, registros)
        cur.execute(
            f"""
            UPDATE cont_asiento a
            JOIN {_TMP_LM_SALDOS} t ON t.id_asiento = a.id_asiento
            SET a.saldo_asiento = t.saldo_asiento
            """
        )
        actualizadas = cur.rowcount if cur.rowcount is not None and cur.rowcount >= 0 else len(registros)
    finally:
        cur.execute(f"DROP TEMPORARY TABLE IF EXISTS {_TMP_LM_SALDOS}")
    return actualizadas


def recalcular_saldo_asiento_cuenta(
    cur,
    dict_cur,
    id_pc: int,
    id_ejercicio: int,
    *,
    tratamiento_anulados: str | None = None,
) -> int:
    """Reescribe el saldo corrido del Libro Mayor (`cont_asiento.saldo_asiento`).

    Siempre acumula **todas** las filas (incluidas `anulado='Si'`), paridad con
    Conta_Info / ``conta_libro_mayor.rpt``. El argumento ``tratamiento_anulados``
    se ignora (compatibilidad de firma); el corrido usa la regla canónica
    ``incluir_neutralizado``.
    """
    del tratamiento_anulados  # corrido LM: siempre incluir anulados (regla canónica)
    return _recalcular_saldo_asiento_setbased(
        cur,
        dict_cur,
        id_ejercicios=[id_ejercicio],
        id_pcs=[id_pc],
    )


def _validar_saldos_libro_mayor_setbased(
    dict_cur,
    id_ejercicios: list[int],
    *,
    tratamiento_anulados: str,
) -> list[dict]:
    """Compara pie denormalizado y último corrido vs teóricos (consultas agregadas)."""
    if not id_ejercicios:
        return []

    placeholders = ",".join(["%s"] * len(id_ejercicios))
    params = list(id_ejercicios)

    teoricos_politica = {
        (to_int_or_none(f["id_pc"]), to_int_or_none(f["id_ejercicio"])): _r2(f.get("saldo_teorico"))
        for f in _saldos_teoricos_agregados(dict_cur, id_ejercicios, tratamiento_anulados=tratamiento_anulados)
    }
    teoricos_libro = {
        (to_int_or_none(f["id_pc"]), to_int_or_none(f["id_ejercicio"])): _r2(f.get("saldo_teorico"))
        for f in _saldos_teoricos_agregados(
            dict_cur, id_ejercicios, tratamiento_anulados=TRATAMIENTO_ANULADOS_LIBRO_MAYOR
        )
    }

    dict_cur.execute(
        f"""
        SELECT es.id_pc, es.id_ejercicio, es.saldo_ejercicio_cta
        FROM cont_ejercicio_saldo_cta es
        WHERE es.id_ejercicio IN ({placeholders})
        """,
        params,
    )
    almacenados = {
        (to_int_or_none(f["id_pc"]), to_int_or_none(f["id_ejercicio"])): _d(f.get("saldo_ejercicio_cta"))
        for f in dict_cur.fetchall() or []
    }

    dict_cur.execute(
        f"""
        SELECT a1.id_pc, a1.id_ejercicio, a1.saldo_asiento
        FROM cont_asiento a1
        LEFT JOIN cont_asiento a2 ON
            a1.id_pc = a2.id_pc
            AND a1.id_ejercicio = a2.id_ejercicio
            AND (
                a2.fecha_asiento > a1.fecha_asiento
                OR (a2.fecha_asiento = a1.fecha_asiento AND a2.nro_asiento > a1.nro_asiento)
                OR (
                    a2.fecha_asiento = a1.fecha_asiento
                    AND a2.nro_asiento = a1.nro_asiento
                    AND a2.id_asiento > a1.id_asiento
                )
            )
        WHERE a1.id_ejercicio IN ({placeholders})
          AND a1.id_pc IS NOT NULL
          AND a2.id_asiento IS NULL
        """,
        params,
    )
    ultimos = {
        (to_int_or_none(f["id_pc"]), to_int_or_none(f["id_ejercicio"])): _d(f.get("saldo_asiento"))
        for f in dict_cur.fetchall() or []
    }

    claves = set(teoricos_politica) | set(teoricos_libro) | set(almacenados) | set(ultimos)
    mismatches: list[dict] = []
    for clave in sorted(claves):
        id_pc, id_ejercicio = clave
        if id_pc is None or id_ejercicio is None:
            continue
        teorico = teoricos_politica.get(clave, Decimal("0"))
        teorico_libro = teoricos_libro.get(clave, Decimal("0"))
        almacenado = almacenados.get(clave, Decimal("0"))
        ultimo = ultimos.get(clave, Decimal("0"))
        if abs(almacenado - teorico) > Decimal("0.005") or abs(ultimo - teorico_libro) > Decimal("0.005"):
            mismatches.append(
                {
                    "id_pc": id_pc,
                    "id_ejercicio": id_ejercicio,
                    "teorico": str(teorico),
                    "teorico_libro_mayor": str(teorico_libro),
                    "saldo_ejercicio_cta": str(almacenado),
                    "ultimo_saldo_asiento": str(ultimo),
                }
            )
    return mismatches


def recalcular_libro_mayor(
    base_empresa: str,
    *,
    id_ejercicios: list[int],
    tratamiento_anulados: str = "incluir_neutralizado",
    usuario: str = "",
) -> dict:
    """Alinea saldos derivados y corrido del Libro Mayor en una transacción.

    Pie (``cont_ejercicio_saldo_cta`` / ``cont_periodo_saldo_cta``) y corrido
    (``cont_asiento.saldo_asiento``) respetan ``tratamiento_anulados`` (default
    ``incluir_neutralizado``). Con la política por defecto, pie == último corrido.
    El corrido del Libro Mayor usa ``TRATAMIENTO_ANULADOS_LIBRO_MAYOR`` (alias).
    """
    ejercicios = sorted(
        {
            id_ejercicio
            for valor in id_ejercicios
            if (id_ejercicio := to_int_or_none(valor)) is not None
        }
    )
    if not ejercicios:
        raise CorreccionContableError("Debe indicar al menos un ejercicio válido.")

    placeholders = ",".join(["%s"] * len(ejercicios))
    metricas = {
        "base_empresa": str_or_default(base_empresa),
        "usuario": str_or_default(usuario),
        "ejercicios": ejercicios,
        "tratamiento_anulados": tratamiento_anulados,
        "tratamiento_anulados_libro_mayor": TRATAMIENTO_ANULADOS_LIBRO_MAYOR,
        "cuentas_tocadas": 0,
        "filas_saldo_asiento": 0,
        "periodos_tocados": 0,
        "mismatches_finales": [],
    }
    pool = get_mysql_pool()
    with pool.get_connection(base_empresa) as conn:
        try:
            conn.autocommit(False)
            cur = conn.cursor()
            dict_cur = conn.cursor(MySQLdb.cursors.DictCursor)
            dict_cur.execute(
                f"""
                SELECT DISTINCT id_pc, id_ejercicio
                FROM cont_asiento
                WHERE id_ejercicio IN ({placeholders}) AND id_pc IS NOT NULL
                ORDER BY id_ejercicio, id_pc
                """,
                ejercicios,
            )
            cuentas = [
                (to_int_or_none(fila.get("id_pc")), to_int_or_none(fila.get("id_ejercicio")))
                for fila in dict_cur.fetchall() or []
            ]
            cuentas = [(id_pc, id_ej) for id_pc, id_ej in cuentas if id_pc is not None and id_ej is not None]

            dict_cur.execute(
                f"""
                SELECT DISTINCT id_pc, id_ejercicio, id_periodo
                FROM cont_asiento
                WHERE id_ejercicio IN ({placeholders})
                  AND id_pc IS NOT NULL AND id_periodo IS NOT NULL
                ORDER BY id_ejercicio, id_pc, id_periodo
                """,
                ejercicios,
            )
            periodos = [
                (
                    to_int_or_none(fila.get("id_pc")),
                    to_int_or_none(fila.get("id_ejercicio")),
                    to_int_or_none(fila.get("id_periodo")),
                )
                for fila in dict_cur.fetchall() or []
            ]
            periodos = [
                (id_pc, id_ej, id_per)
                for id_pc, id_ej, id_per in periodos
                if id_pc is not None and id_ej is not None and id_per is not None
            ]

            for fila in _saldos_teoricos_agregados(
                dict_cur, ejercicios, tratamiento_anulados=tratamiento_anulados
            ):
                id_pc = to_int_or_none(fila.get("id_pc"))
                id_ejercicio = to_int_or_none(fila.get("id_ejercicio"))
                if id_pc is None or id_ejercicio is None:
                    continue
                _guardar_saldo_ejercicio(
                    cur,
                    dict_cur,
                    id_pc,
                    id_ejercicio,
                    _r2(fila.get("saldo_teorico")),
                )

            for fila in _saldos_teoricos_periodos_agregados(
                dict_cur, ejercicios, tratamiento_anulados=tratamiento_anulados
            ):
                id_pc = to_int_or_none(fila.get("id_pc"))
                id_ejercicio = to_int_or_none(fila.get("id_ejercicio"))
                id_periodo = to_int_or_none(fila.get("id_periodo"))
                if id_pc is None or id_ejercicio is None or id_periodo is None:
                    continue
                _guardar_saldo_periodo(
                    cur,
                    dict_cur,
                    id_pc,
                    id_ejercicio,
                    id_periodo,
                    _r2(fila.get("saldo_teorico")),
                )

            metricas["filas_saldo_asiento"] = _recalcular_saldo_asiento_setbased(
                cur,
                dict_cur,
                id_ejercicios=ejercicios,
            )
            metricas["cuentas_tocadas"] = len(cuentas)
            metricas["periodos_tocados"] = len(periodos)

            metricas["mismatches_finales"] = _validar_saldos_libro_mayor_setbased(
                dict_cur,
                ejercicios,
                tratamiento_anulados=tratamiento_anulados,
            )
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            try:
                conn.autocommit(True)
            except Exception:
                pass

    metricas["total_mismatches_finales"] = len(metricas["mismatches_finales"])
    return metricas


def _fecha_ui(dt) -> str:
    if dt is None:
        return ""
    return timezone.localtime(dt).strftime("%d/%m/%Y %H:%M")


class _RepoLectura:
    """Cache de lecturas SELECT para reconstrucción (portado del script validado)."""

    def __init__(self, conn):
        self.conn = conn
        self._matriz: dict[int, Optional[int]] = {}
        self._prov_pc: dict[Any, Optional[int]] = {}
        self._cli_pc: dict[Any, Optional[int]] = {}
        self._gasto_pc: dict[Any, Optional[int]] = {}
        self._art: dict[Any, dict | None] = {}
        self._percep_cli_pc: dict[Any, Optional[int]] = {}
        self._caja: dict[tuple, Optional[int]] = {}
        self._impuesto_pc: dict[Any, Optional[int]] = {}
        self._deuda_pc: dict[Any, Optional[int]] = {}
        self._percepcion_pc: dict[Any, Optional[int]] = {}
        self._cuenta_banco_pc: dict[Any, Optional[int]] = {}
        self._ejercicio: dict[Any, dict | None] = {}
        self._periodo: dict[tuple, dict | None] = {}
        self._saldo_pc: dict[int, Optional[str]] = {}
        self._ejercicios_cerrados: set[int] | None = None
        self._ejercicio_activo: Optional[int] = None

    def cur(self):
        return self.conn.cursor(MySQLdb.cursors.DictCursor)

    def matriz(self, idm: int) -> Optional[int]:
        if idm not in self._matriz:
            cur = self.cur()
            cur.execute("SELECT id_pc FROM cont_paramatriz WHERE id_paramatriz=%s", (idm,))
            row = cur.fetchone()
            self._matriz[idm] = to_int_or_none(row["id_pc"]) if row else None
        return self._matriz[idm]

    def proveedor_pc(self, codigo) -> Optional[int]:
        if codigo not in self._prov_pc:
            cur = self.cur()
            cur.execute("SELECT id_pc FROM proveedor WHERE codigo=%s", (codigo,))
            rows = cur.fetchall()
            self._prov_pc[codigo] = to_int_or_none(rows[0]["id_pc"]) if len(rows) == 1 else None
        return self._prov_pc[codigo]

    def cliente_pc(self, codigo) -> Optional[int]:
        if codigo not in self._cli_pc:
            cur = self.cur()
            cur.execute("SELECT id_pc FROM cliente WHERE Codigo=%s", (codigo,))
            rows = cur.fetchall()
            self._cli_pc[codigo] = to_int_or_none(rows[0]["id_pc"]) if len(rows) == 1 else None
        return self._cli_pc[codigo]

    def gasto_pc(self, codigo) -> Optional[int]:
        if codigo not in self._gasto_pc:
            cur = self.cur()
            cur.execute("SELECT id_pc FROM gastos WHERE Codigo=%s", (codigo,))
            row = cur.fetchone()
            self._gasto_pc[codigo] = to_int_or_none(row["id_pc"]) if row else None
        return self._gasto_pc[codigo]

    def articulo(self, idart):
        if idart not in self._art:
            cur = self.cur()
            cur.execute(
                "SELECT idart, id_pc_comp, id_pc_vta, cod_gasto FROM articulo WHERE idart=%s",
                (idart,),
            )
            self._art[idart] = cur.fetchone()
        return self._art[idart]

    def percep_cli_pc(self, id_percep_cli_tipo) -> Optional[int]:
        if id_percep_cli_tipo not in self._percep_cli_pc:
            cur = self.cur()
            cur.execute(
                """SELECT a.id_pc
                   FROM percep_cli_tipo t
                   JOIN percep_cli_abm a ON a.id_percep_cli_abm = t.id_percep_cli_abm
                   WHERE t.id_percep_cli_tipo=%s""",
                (id_percep_cli_tipo,),
            )
            row = cur.fetchone()
            self._percep_cli_pc[id_percep_cli_tipo] = (
                to_int_or_none(row["id_pc"]) if row else None
            )
        return self._percep_cli_pc[id_percep_cli_tipo]

    def impuesto_pc(self, id_impuesto) -> Optional[int]:
        if id_impuesto not in self._impuesto_pc:
            cur = self.cur()
            cur.execute("SELECT id_pc_deuda FROM impuesto WHERE id_impuesto=%s", (id_impuesto,))
            row = cur.fetchone()
            self._impuesto_pc[id_impuesto] = to_int_or_none(row["id_pc_deuda"]) if row else None
        return self._impuesto_pc[id_impuesto]

    def deuda_pc(self, id_deuda) -> Optional[int]:
        if id_deuda not in self._deuda_pc:
            cur = self.cur()
            cur.execute("SELECT id_pc FROM deuda_abm WHERE id_deuda_abm=%s", (id_deuda,))
            row = cur.fetchone()
            self._deuda_pc[id_deuda] = to_int_or_none(row["id_pc"]) if row else None
        return self._deuda_pc[id_deuda]

    def percepcion_pc(self, id_percepcion) -> Optional[int]:
        if id_percepcion not in self._percepcion_pc:
            cur = self.cur()
            cur.execute(
                "SELECT id_pc FROM percepcion_abm WHERE id_percepcion_abm=%s",
                (id_percepcion,),
            )
            row = cur.fetchone()
            self._percepcion_pc[id_percepcion] = to_int_or_none(row["id_pc"]) if row else None
        return self._percepcion_pc[id_percepcion]

    def caja_pc(self, id_caja, dolares: bool = False) -> Optional[int]:
        clave = (id_caja, dolares)
        if clave not in self._caja:
            campo = "id_pc_dolares" if dolares else "id_pc"
            cur = self.cur()
            cur.execute(f"SELECT {campo} AS id_pc FROM caja_abm WHERE id_caja=%s", (id_caja,))
            row = cur.fetchone()
            self._caja[clave] = to_int_or_none(row["id_pc"]) if row else None
        return self._caja[clave]

    def cuenta_banco_pc(self, codigo) -> Optional[int]:
        if codigo not in self._cuenta_banco_pc:
            cur = self.cur()
            cur.execute("SELECT id_pc FROM cuenta_banco WHERE CodCuenta=%s", (codigo,))
            row = cur.fetchone()
            self._cuenta_banco_pc[codigo] = to_int_or_none(row["id_pc"]) if row else None
        return self._cuenta_banco_pc[codigo]

    def saldo_pc(self, id_pc: int) -> Optional[str]:
        if id_pc not in self._saldo_pc:
            cur = self.cur()
            cur.execute("SELECT saldo_pc FROM cont_pc WHERE id_pc=%s", (id_pc,))
            row = cur.fetchone()
            valor = str_or_default(row["saldo_pc"] if row else None, "")
            self._saldo_pc[id_pc] = valor or None
        return self._saldo_pc[id_pc]

    def ejercicio_por_fecha(self, fecha) -> dict | None:
        fecha_norm = to_date_or_none(fecha)
        if not fecha_norm:
            return None
        if fecha_norm not in self._ejercicio:
            cur = self.cur()
            cur.execute(
                """SELECT id_ejercicio, descripcion_ejercicio, cerrado, nro_asiento_ejercicio
                   FROM cont_ejercicio
                   WHERE %s BETWEEN fecdesde_ejercicio AND fechasta_ejercicio
                   ORDER BY id_ejercicio DESC LIMIT 1""",
                (fecha_norm,),
            )
            self._ejercicio[fecha_norm] = cur.fetchone()
        return self._ejercicio[fecha_norm]

    def periodo(self, id_ejercicio: int, fecha) -> dict | None:
        fecha_norm = to_date_or_none(fecha)
        clave = (id_ejercicio, fecha_norm)
        if clave not in self._periodo:
            cur = self.cur()
            cur.execute(
                """SELECT id_periodo, descripcion_periodo, cerrado
                   FROM cont_periodo
                   WHERE id_ejercicio=%s
                     AND %s BETWEEN fecdesde_periodo AND fechasta_periodo
                   ORDER BY id_periodo DESC LIMIT 1""",
                (id_ejercicio, fecha_norm),
            )
            self._periodo[clave] = cur.fetchone()
        return self._periodo[clave]

    def ejercicios_cerrados(self) -> set[int]:
        if self._ejercicios_cerrados is None:
            cur = self.cur()
            cur.execute(
                "SELECT id_ejercicio FROM cont_ejercicio WHERE COALESCE(cerrado,'No')='Si'"
            )
            self._ejercicios_cerrados = {
                to_int_or_none(r["id_ejercicio"]) for r in cur.fetchall() if r.get("id_ejercicio")
            }
        return self._ejercicios_cerrados

    def ejercicio_activo_id(self) -> Optional[int]:
        if self._ejercicio_activo is None:
            cur = self.cur()
            cur.execute(
                """SELECT id_ejercicio FROM cont_ejercicio
                   WHERE COALESCE(activo_ejercicio,'No')='Si'
                   ORDER BY id_ejercicio DESC LIMIT 1"""
            )
            row = cur.fetchone()
            self._ejercicio_activo = to_int_or_none(row["id_ejercicio"]) if row else None
        return self._ejercicio_activo

    def nro_asiento_ejercicio(self, id_ejercicio: int) -> int:
        cur = self.cur()
        cur.execute(
            "SELECT nro_asiento_ejercicio FROM cont_ejercicio WHERE id_ejercicio=%s",
            (id_ejercicio,),
        )
        row = cur.fetchone()
        return to_int_or_none(row["nro_asiento_ejercicio"]) if row else 0


def _add_renglon(renglones: dict, id_pc, debe=0, haber=0) -> None:
    if id_pc is None:
        renglones.setdefault("_ERR_", []).append(("cuenta_nula", str(debe), str(haber)))
        return
    key = int(id_pc)
    renglones[key][0] += _d(debe)
    renglones[key][1] += _d(haber)


def reconstruir_factura(repo: _RepoLectura, cab: dict) -> tuple[dict, list]:
    renglones: dict[Any, list] = defaultdict(lambda: [Decimal("0"), Decimal("0")])
    errores: list[str] = []
    codmov = cab["CodigoMovimiento"]

    cur = repo.cur()
    cur.execute(
        "SELECT IDArt, PrecioNetoxR, CodigoGasto FROM stock WHERE CodigoMovimiento=%s",
        (codmov,),
    )
    filas = cur.fetchall()
    if not filas:
        errores.append("sin_detalle_stock")
    for f in filas:
        art = repo.articulo(f["IDArt"])
        cuenta = None
        if art and to_int_or_none(art.get("id_pc_comp")) not in (None, 0):
            cuenta = to_int_or_none(art["id_pc_comp"])
        elif art and to_int_or_none(art.get("cod_gasto")) not in (None, 0):
            cuenta = repo.gasto_pc(art["cod_gasto"])
            if cuenta is None:
                cuenta = repo.matriz(24)
        else:
            cuenta = repo.matriz(13)
        _add_renglon(renglones, cuenta, debe=f["PrecioNetoxR"])

    for campo, idm in (("IVA1", 10), ("IVA2", 11), ("IVA3", 12), ("sobretasa_iva", 50)):
        val = _d(cab.get(campo))
        if val > 0:
            _add_renglon(renglones, repo.matriz(idm), debe=val)
    for campo, idm in (
        ("impuesto_interno", 6),
        ("OtrosImp", 15),
        ("PercepIVA", 16),
        ("PercepGan", 17),
    ):
        val = _d(cab.get(campo))
        if val > 0:
            _add_renglon(renglones, repo.matriz(idm), debe=val)

    cur.execute(
        """SELECT p.importe_percep, pr.id_pc
           FROM percep_prov p
           LEFT JOIN provincia pr ON pr.codProvincia = p.id_jurisdiccion
           WHERE p.codigo_movimiento=%s AND COALESCE(p.anulado,'No')<>'Si'""",
        (codmov,),
    )
    for f in cur.fetchall():
        _add_renglon(renglones, f["id_pc"], debe=f["importe_percep"])

    desc = _d(cab.get("TotalDesc"))
    if desc > 0:
        _add_renglon(renglones, repo.matriz(20), haber=desc)

    importe_total = _d(cab.get("ImporteCompra"))
    if to_int_or_none(cab.get("id_condcompra")) == 1:
        errores.append("contado_requiere_caja")
    else:
        cuenta_prov = repo.proveedor_pc(cab["Codigo"])
        if cuenta_prov is None:
            cuenta_prov = repo.matriz(28)
        _add_renglon(renglones, cuenta_prov, haber=importe_total)

    return renglones, errores


def reconstruir_factura_venta(repo: _RepoLectura, cab: dict) -> tuple[dict, list]:
    """Reconstruye asiento de factura de venta (concepto 1) desde tablas persistidas.

    Espejo invertido de ``reconstruir_factura`` (compras): neto/IVA/percepciones en HABER,
    cliente o caja (contado) en DEBE. Gating de contabilidad: punto_venta.cont (check).
    """
    renglones: dict[Any, list] = defaultdict(lambda: [Decimal("0"), Decimal("0")])
    errores: list[str] = []
    codmov = cab["CodigoMovimiento"]
    cur = repo.cur()

    cur.execute(
        "SELECT IDArt, PrecioNetoxR FROM stock WHERE CodigoMovimiento=%s",
        (codmov,),
    )
    filas = cur.fetchall()
    if not filas:
        errores.append("sin_detalle_stock")
    for f in filas:
        art = repo.articulo(f["IDArt"])
        cuenta = None
        if art and to_int_or_none(art.get("id_pc_vta")) not in (None, 0):
            cuenta = to_int_or_none(art["id_pc_vta"])
        else:
            cuenta = repo.matriz(4)
        _add_renglon(renglones, cuenta, haber=f["PrecioNetoxR"])

    for campo, idm in (("IVA1", 2), ("IVA2", 3)):
        val = _d(cab.get(campo))
        if val > 0:
            _add_renglon(renglones, repo.matriz(idm), haber=val)

    for campo, idm in (("impuesto_interno", 6), ("OtrosImp", 15)):
        val = _d(cab.get(campo))
        if val > 0:
            _add_renglon(renglones, repo.matriz(idm), haber=val)

    cur.execute(
        """SELECT p.importe_percep_cli, p.id_percep_cli_tipo
           FROM percep_cli p
           WHERE p.codigo_movimiento=%s AND COALESCE(p.anulado,'No')<>'Si'
             AND COALESCE(p.importe_percep_cli,0)<>0""",
        (codmov,),
    )
    for f in cur.fetchall():
        cuenta = repo.percep_cli_pc(f["id_percep_cli_tipo"]) or repo.matriz(18)
        _add_renglon(renglones, cuenta, haber=f["importe_percep_cli"])

    desc = _d(cab.get("ImpDesc1")) + _d(cab.get("ImpDesc2"))
    if desc > 0:
        _add_renglon(renglones, repo.matriz(8), debe=desc)

    importe_total = _d(cab.get("ImporteVenta"))
    if to_int_or_none(cab.get("id_condventa")) == 1:
        cur.execute(
            """SELECT ingreso, id_caja_abm_origen
               FROM caja
               WHERE codigo_movimiento=%s AND COALESCE(anulado,'No')<>'Si'
                 AND COALESCE(ingreso,0)<>0""",
            (codmov,),
        )
        filas_caja = cur.fetchall()
        if not filas_caja:
            errores.append("contado_sin_caja")
        for fila in filas_caja:
            cuenta = repo.caja_pc(fila["id_caja_abm_origen"]) or repo.matriz(23)
            _add_renglon(renglones, cuenta, debe=fila["ingreso"])
    else:
        cuenta_cli = repo.cliente_pc(cab["Codigo"])
        if cuenta_cli is None:
            cuenta_cli = repo.matriz(1)
        _add_renglon(renglones, cuenta_cli, debe=importe_total)

    return renglones, errores


def reconstruir_rec(repo: _RepoLectura, cab: dict) -> tuple[dict, list]:
    """Reconstruye asiento de REC (concepto 5) desde medios de cobro persistidos."""
    renglones: dict[Any, list] = defaultdict(lambda: [Decimal("0"), Decimal("0")])
    errores: list[str] = []
    codmov = cab["CodigoMovimiento"]
    cur = repo.cur()

    cur.execute(
        """SELECT ingreso, id_caja_abm_origen, id_chequetercero
           FROM caja
           WHERE codigo_movimiento=%s AND COALESCE(anulado,'No')<>'Si'
             AND COALESCE(ingreso,0)<>0""",
        (codmov,),
    )
    for fila in cur.fetchall():
        # Entrega de cheque tercero: se imputa desde chequetercero, no como efectivo.
        if fila.get("id_chequetercero") not in (None, 0):
            continue
        cuenta = repo.caja_pc(fila["id_caja_abm_origen"]) or repo.matriz(23)
        _add_renglon(renglones, cuenta, debe=fila["ingreso"])

    cur.execute(
        """SELECT Importe FROM chequetercero
           WHERE CodigoMovimientoREC=%s AND COALESCE(Anulado,'No')<>'Si'""",
        (codmov,),
    )
    for fila in cur.fetchall():
        _add_renglon(renglones, repo.matriz(5) or repo.matriz(23), debe=fila["Importe"])

    cur.execute(
        """SELECT importe_transf, id_cuentabancaria FROM transferencia
           WHERE codigo_movimiento=%s AND COALESCE(anulado,'No')<>'Si'""",
        (codmov,),
    )
    for fila in cur.fetchall():
        cuenta = repo.cuenta_banco_pc(fila["id_cuentabancaria"]) or repo.matriz(22)
        _add_renglon(renglones, cuenta, debe=fila["importe_transf"])

    cur.execute(
        """SELECT Importe, CodRetencion FROM retenciones
           WHERE codigo_movimiento=%s AND COALESCE(Anulado,'No')<>'Si'""",
        (codmov,),
    )
    for fila in cur.fetchall():
        cur.execute(
            "SELECT id_pc FROM tipo_retencion_cli WHERE CodRetencion=%s LIMIT 1",
            (fila["CodRetencion"],),
        )
        row_pc = cur.fetchone()
        cuenta = to_int_or_none(row_pc["id_pc"]) if row_pc else repo.matriz(18)
        _add_renglon(renglones, cuenta, debe=fila["Importe"])

    cur.execute(
        """SELECT importe_tc_comprobante FROM tc_comprobante
           WHERE codigo_movimiento=%s AND COALESCE(anulado,'No')<>'Si'""",
        (codmov,),
    )
    for fila in cur.fetchall():
        _add_renglon(renglones, repo.matriz(5), debe=fila["importe_tc_comprobante"])

    total = _d(cab.get("ImporteCobro") or cab.get("TotalRecibo") or cab.get("ImporteVenta"))
    if total <= 0:
        errores.append("rec_sin_total")
    cuenta_cli = repo.cliente_pc(cab["Codigo"]) or repo.matriz(1)
    _add_renglon(renglones, cuenta_cli, haber=total)

    if not any(k != "_ERR_" for k in renglones):
        errores.append("rec_sin_medios")

    return renglones, errores


def reconstruir_op(repo: _RepoLectura, cab: dict) -> tuple[dict, list]:
    renglones: dict[Any, list] = defaultdict(lambda: [Decimal("0"), Decimal("0")])
    errores: list[str] = []
    codmov = cab["CodigoMovimiento"]
    tipo_op = str_or_default(cab.get("TipoOP")).lower()
    cur = repo.cur()

    cur.execute(
        """SELECT tipo_oe, importe_oe, id_impuesto, id_gasto, id_deuda_abm,
                  id_percepcion, importe_percepcion
           FROM otro_egreso
           WHERE codigo_movimiento_op=%s AND COALESCE(anulado,'No')<>'Si'""",
        (codmov,),
    )
    for fila in cur.fetchall():
        if fila["id_percepcion"] is not None:
            cuenta = repo.percepcion_pc(fila["id_percepcion"]) or repo.matriz(49)
            importe = fila["importe_percepcion"]
        elif fila["tipo_oe"] == "Impuestos":
            cuenta = repo.impuesto_pc(fila["id_impuesto"]) or repo.matriz(27)
            importe = fila["importe_oe"]
        elif fila["tipo_oe"] == "Otros Egresos":
            cuenta = repo.gasto_pc(fila["id_gasto"]) or repo.matriz(24)
            importe = fila["importe_oe"]
        elif fila["tipo_oe"] == "Deudas":
            cuenta = repo.deuda_pc(fila["id_deuda_abm"]) or repo.matriz(43)
            importe = fila["importe_oe"]
        else:
            errores.append(f"tipo_oe_desconocido:{fila['tipo_oe']}")
            _add_renglon(renglones, None, debe=fila["importe_oe"])
            continue
        _add_renglon(renglones, cuenta, debe=importe)

    if tipo_op in ("a cuenta", "imputacion"):
        _add_renglon(renglones, repo.proveedor_pc(cab["Codigo"]), debe=cab.get("TotalOP"))
    elif tipo_op != "egreso":
        errores.append(f"tipo_op_desconocido:{tipo_op}")

    for tabla, matriz in (
        ("retenciones_prov", 30),
        ("retenciones_provg", 29),
        ("retenciones_prov_IVA", 62),
    ):
        cur.execute(
            f"""SELECT Importe FROM {tabla}
                WHERE codigo_movimiento=%s AND COALESCE(anulado,'No')<>'Si'""",
            (codmov,),
        )
        for fila in cur.fetchall():
            _add_renglon(renglones, repo.matriz(matriz), haber=fila["Importe"])

    cur.execute(
        """SELECT egreso, moneda, id_caja_abm_origen
           FROM caja
           WHERE codigo_movimiento=%s AND COALESCE(anulado,'No')<>'Si'
             AND COALESCE(egreso,0)<>0
             AND id_chequetercero IS NULL""",
        (codmov,),
    )
    for fila in cur.fetchall():
        es_dolar = str_or_default(fila.get("moneda")).lower() in ("dolar", "dólar", "usd")
        if es_dolar:
            errores.append("efectivo_dolares_persistido")
        _add_renglon(
            renglones,
            repo.caja_pc(fila["id_caja_abm_origen"], dolares=es_dolar),
            haber=fila["egreso"],
        )

    cur.execute(
        """SELECT Importe FROM chequepropio
           WHERE CodigoMovimientoOP=%s AND COALESCE(Anulado,'No')<>'Si'""",
        (codmov,),
    )
    for fila in cur.fetchall():
        _add_renglon(renglones, repo.matriz(32), haber=fila["Importe"])

    cur.execute(
        """SELECT Importe, id_caja FROM chequetercero
           WHERE CodigoMovimientoOP=%s AND COALESCE(Anulado,'No')<>'Si'""",
        (codmov,),
    )
    for fila in cur.fetchall():
        cuenta = repo.caja_pc(fila["id_caja"]) if fila.get("id_caja") else None
        _add_renglon(renglones, cuenta or repo.matriz(31), haber=fila["Importe"])

    cur.execute(
        """SELECT importe_transf, id_cuentabancaria FROM transferencia
           WHERE codigo_movimiento=%s AND COALESCE(anulado,'No')<>'Si'""",
        (codmov,),
    )
    for fila in cur.fetchall():
        cuenta = repo.cuenta_banco_pc(fila["id_cuentabancaria"])
        _add_renglon(renglones, cuenta or repo.matriz(42), haber=fila["importe_transf"])

    return renglones, errores


def _ejercicios_en_alcance(alcance: dict, politica: dict, repo: _RepoLectura) -> Optional[set[int]]:
    """Conjunto de id_ejercicio permitidos; ``None`` = sin filtro (histórico)."""
    modo = politica.get("alcance_recompute", "ejercicio_seleccionado")
    if modo == "ejercicio_seleccionado":
        id_ej = to_int_or_none(alcance.get("id_ejercicio"))
        return {id_ej} if id_ej is not None else set()
    if modo == "ejercicio_activo":
        activo = repo.ejercicio_activo_id()
        if activo is not None:
            return {activo}
        id_ej = to_int_or_none(alcance.get("id_ejercicio"))
        return {id_ej} if id_ej is not None else set()
    return None


def _marcar_exclusiones(items: list[dict], politica: dict, repo: _RepoLectura) -> None:
    if politica.get("ejercicios_cerrados") != "no_tocar":
        return
    cerrados = repo.ejercicios_cerrados()
    for item in items:
        if item.get("excluido"):
            continue
        clave = item.get("clave") or {}
        id_ej = to_int_or_none(clave.get("id_ejercicio"))
        if id_ej is None:
            vn = item.get("valor_nuevo") or {}
            if isinstance(vn, dict):
                id_ej = to_int_or_none(vn.get("id_ejercicio"))
        if id_ej in cerrados:
            item["excluido"] = True
            item["motivo_exclusion"] = "ejercicio_cerrado"


def _exige_marcador_anulacion(tipo_comprobante, tipo_op) -> bool:
    if str_or_default(tipo_comprobante).upper() != "OP":
        return True
    return str_or_default(tipo_op).strip().lower() != "egreso"


def _evaluar_problemas_anulacion_cm(
    cur,
    cm,
    *,
    tipo_comprobante=None,
    tipo_op=None,
) -> tuple[list[str], dict[str, Any]]:
    """Paridad con check integridad_anulacion_compra_pago (AUD-LECT-23)."""
    if tipo_comprobante is None or tipo_op is None:
        cur.execute(
            """
            SELECT TipoComprobante, TipoOP FROM cuentaproveedor
            WHERE CodigoMovimiento = %s
            LIMIT 1
            """,
            (cm,),
        )
        row_cp = cur.fetchone()
        if isinstance(row_cp, dict):
            tipo_comprobante = row_cp.get("TipoComprobante")
            tipo_op = row_cp.get("TipoOP")
        elif row_cp is not None:
            tipo_comprobante = row_cp[0]
            tipo_op = row_cp[1]

    cur.execute(
        """
        SELECT COUNT(*) AS cnt FROM cuentaproveedor
        WHERE CodigoMovimiento = 0 AND codigo_movimiento_anul = %s
        """,
        (cm,),
    )
    row_m = cur.fetchone()
    tiene_marcador = (row_m.get("cnt") if isinstance(row_m, dict) else row_m[0] or 0) > 0

    cur.execute(
        """
        SELECT
          SUM(CASE WHEN COALESCE(anulado, 'No') <> 'Si' THEN 1 ELSE 0 END) AS pendientes,
          COUNT(*) AS total
        FROM cont_asiento
        WHERE codigo_movimiento = %s
        """,
        (cm,),
    )
    row_a = cur.fetchone()
    if isinstance(row_a, dict):
        pendientes_orig = to_int_or_none(row_a.get("pendientes")) or 0
        total_orig = to_int_or_none(row_a.get("total")) or 0
    else:
        pendientes_orig = to_int_or_none(row_a[0]) or 0
        total_orig = to_int_or_none(row_a[1]) or 0

    cur.execute(
        """
        SELECT codigo_movimiento,
               SUM(COALESCE(debe_asiento, 0)) AS d,
               SUM(COALESCE(haber_asiento, 0)) AS h
        FROM cont_asiento
        WHERE codigo_movimiento = %s
        GROUP BY codigo_movimiento
        """,
        (cm,),
    )
    orig_tot = cur.fetchone()

    cur.execute(
        """
        SELECT codigo_movimiento,
               SUM(COALESCE(debe_asiento, 0)) AS d,
               SUM(COALESCE(haber_asiento, 0)) AS h
        FROM cont_asiento
        WHERE codigo_movimiento_anul = %s
          AND id_concepto_asiento IN (4, 8)
          AND COALESCE(anulado, 'No') = 'No'
          AND COALESCE(codigo_movimiento, 0) <> 0
        GROUP BY codigo_movimiento
        """,
        (cm,),
    )
    contra_tot = cur.fetchone()

    problemas: list[str] = []
    if not tiene_marcador and _exige_marcador_anulacion(tipo_comprobante, tipo_op):
        problemas.append("falta_marcador_cuentaproveedor_cm0")
    # Solo si hay renglones pendientes de marcar (no vacíos: COUNT=0 no es problema de anulado).
    if total_orig > 0 and pendientes_orig > 0:
        problemas.append("asiento_original_no_anulado")
    if contra_tot is None:
        problemas.append("falta_contra_asiento")
    elif orig_tot is not None:
        if isinstance(orig_tot, dict):
            od = to_decimal_or_none(orig_tot.get("d")) or Decimal("0")
            oh = to_decimal_or_none(orig_tot.get("h")) or Decimal("0")
            cd = to_decimal_or_none(contra_tot.get("d")) or Decimal("0")
            ch = to_decimal_or_none(contra_tot.get("h")) or Decimal("0")
        else:
            od = to_decimal_or_none(orig_tot[1]) or Decimal("0")
            oh = to_decimal_or_none(orig_tot[2]) or Decimal("0")
            cd = to_decimal_or_none(contra_tot[1]) or Decimal("0")
            ch = to_decimal_or_none(contra_tot[2]) or Decimal("0")
        if abs(od - ch) > Decimal("0.005") or abs(oh - cd) > Decimal("0.005"):
            problemas.append("contra_no_invierte_original")

    return problemas, {"orig_tot": orig_tot, "contra_tot": contra_tot}


def _reconstruir_renglones_comprobante_anulado(
    repo: _RepoLectura,
    cab: dict,
) -> tuple[list[dict], dict | None]:
    """Reconstruye renglones del asiento original desde cabecera anulada (FA/FC/OP).

    Devuelve renglones no-cero ``{id_pc, debe_asiento, haber_asiento}`` y metadatos
    del asiento, o ``([], None)`` si no es reconstruible o no balancea.
    """
    tipo = str_or_default(cab.get("TipoComprobante"))
    if tipo in TIPOS_FACTURA:
        renglones, errores = reconstruir_factura(repo, cab)
    elif tipo == "OP":
        renglones, errores = reconstruir_op(repo, cab)
    else:
        return [], None

    if "_ERR_" in renglones or "contado_requiere_caja" in errores:
        return [], None

    debe = _r2(sum(v[0] for k, v in renglones.items() if k != "_ERR_"))
    haber = _r2(sum(v[1] for k, v in renglones.items() if k != "_ERR_"))
    dif = _r2(debe - haber)
    if abs(dif) > Q2:
        if abs(dif) <= UMBRAL_REDONDEO:
            if dif > 0:
                _add_renglon(renglones, REDONDEO_PC, haber=dif)
            else:
                _add_renglon(renglones, REDONDEO_PC, debe=-dif)
        else:
            return [], None

    fecha = cab.get("Fecha")
    ejercicio = repo.ejercicio_por_fecha(fecha)
    if not ejercicio:
        return [], None
    id_ejercicio = to_int_or_none(ejercicio["id_ejercicio"])
    if id_ejercicio is None:
        return [], None

    concepto = CONCEPTO.get(tipo, 3)
    desc_concepto = DESC_CONCEPTO.get(concepto, "Compra")
    nro_comp = cab.get("NroComprobante")
    if tipo == "OP":
        desc_asiento = (
            f"{str_or_default(cab.get('TipoOP')).strip()} - Nro Comp. OP - {nro_comp}"
        )
    else:
        desc_asiento = f"Compra - Nro Comp. {nro_comp}"

    renglones_out: list[dict] = []
    for id_pc in sorted(k for k in renglones if k != "_ERR_"):
        vdebe, vhaber = _r2(renglones[id_pc][0]), _r2(renglones[id_pc][1])
        if vdebe == 0 and vhaber == 0:
            continue
        renglones_out.append(
            {
                "id_pc": int(id_pc),
                "debe_asiento": str(vdebe),
                "haber_asiento": str(vhaber),
            }
        )

    if not renglones_out:
        return [], None

    meta = {
        "id_ejercicio": id_ejercicio,
        "fecha_asiento": to_date_or_none(fecha),
        "desc_asiento": desc_asiento,
        "concepto": concepto,
        "desc_concepto": desc_concepto,
    }
    return renglones_out, meta


def _plan_reparacion_anulaciones(
    conn,
    repo: _RepoLectura,
    politica: dict,
    alcance: dict,
) -> list[dict]:
    """Plan REC-19: reparación de anulaciones incompletas (100 % SELECT)."""
    del conn  # lectura vía repo
    ejercicios_alcance = _ejercicios_en_alcance(alcance, politica, repo)
    cur = repo.cur()
    cur.execute(
        """
        SELECT cp.CodigoMovimiento, cp.TipoComprobante, cp.NroComprobante, cp.Fecha,
               cp.CodSucursal, cp.Codigo, cp.ImporteCompra, cp.ImportePago, cp.TipoOP
        FROM cuentaproveedor cp
        JOIN sucursales s ON s.id_sucursal = cp.CodSucursal
        WHERE s.cont = 'Si'
          AND COALESCE(cp.Anulado, 'No') = 'Si'
          AND cp.TipoComprobante IN ('FA', 'FC', 'OP')
          AND COALESCE(cp.CodigoMovimiento, 0) <> 0
        """
    )
    originales = cur.fetchall()
    items: list[dict] = []

    for row in originales:
        cm = row.get("CodigoMovimiento") if isinstance(row, dict) else row[0]
        cm_str = str_or_default(cm)
        tipo = str_or_default(row.get("TipoComprobante") if isinstance(row, dict) else row[1])
        nro_comp = str_or_default(row.get("NroComprobante") if isinstance(row, dict) else row[2])
        fecha = row.get("Fecha") if isinstance(row, dict) else row[3]
        tipo_op = str_or_default(row.get("TipoOP") if isinstance(row, dict) else row[8])

        if ejercicios_alcance is not None:
            ejercicio = repo.ejercicio_por_fecha(fecha)
            id_ej = to_int_or_none(ejercicio["id_ejercicio"]) if ejercicio else None
            if id_ej is None or id_ej not in ejercicios_alcance:
                continue

        problemas, _diag = _evaluar_problemas_anulacion_cm(
            cur, cm, tipo_comprobante=tipo, tipo_op=tipo_op
        )
        if not problemas:
            continue

        detalle_base = {
            "TipoComprobante": tipo,
            "NroComprobante": nro_comp,
            "TipoOP": tipo_op,
            "problemas": problemas,
            "codigo_movimiento_original": cm_str,
        }

        if "contra_no_invierte_original" in problemas:
            items.append(
                {
                    "tabla": "cont_asiento",
                    "clave": {"codigo_movimiento_original": cm_str},
                    "accion": "bloqueado",
                    "valor_anterior": None,
                    "valor_nuevo": None,
                    "delta": "0",
                    "check_id": CHECK_ANULACION,
                    "referencia": "H53",
                    "excluido": True,
                    "bloqueado": True,
                    "motivo_bloqueo": "contra_no_invierte_original",
                    "detalle": detalle_base,
                }
            )
            continue

        if "falta_marcador_cuentaproveedor_cm0" in problemas:
            detalle_marcador = f"Anulacion - {tipo} - {nro_comp}"
            items.append(
                {
                    "tabla": "cuentaproveedor",
                    "clave": {
                        "codigo_movimiento_original": cm_str,
                        "codigo_movimiento_anul": cm_str,
                    },
                    "accion": "insert_marcador",
                    "valor_anterior": None,
                    "valor_nuevo": {
                        "CodigoMovimiento": "0",
                        "codigo_movimiento_anul": cm_str,
                        "Detalle": detalle_marcador,
                        "Anulado": "No",
                        "TipoComprobante": tipo,
                        "NroComprobante": nro_comp,
                        "Fecha": str(fecha) if fecha is not None else "",
                        "CodSucursal": to_int_or_none(
                            row.get("CodSucursal") if isinstance(row, dict) else row[4]
                        ),
                    },
                    "delta": "0",
                    "check_id": CHECK_ANULACION,
                    "referencia": "H53",
                    "excluido": False,
                    "bloqueado": False,
                    "detalle": detalle_base,
                }
            )

        if "asiento_original_no_anulado" in problemas:
            items.append(
                {
                    "tabla": "cont_asiento",
                    "clave": {"codigo_movimiento": cm_str},
                    "accion": "marcar_original_anulado",
                    "valor_anterior": "No",
                    "valor_nuevo": "Si",
                    "delta": "0",
                    "check_id": CHECK_ANULACION,
                    "referencia": "H53",
                    "excluido": False,
                    "bloqueado": False,
                    "detalle": detalle_base,
                }
            )

        if "falta_contra_asiento" in problemas:
            cur.execute(
                """
                SELECT id_pc, id_ejercicio, debe_asiento, haber_asiento,
                       desc_renglon_asiento, desc_concepto_asiento, desc_asiento, fecha_asiento
                FROM cont_asiento
                WHERE codigo_movimiento = %s
                ORDER BY id_pc
                """,
                (cm,),
            )
            renglones_orig = cur.fetchall()
            regenerar_original = False
            renglones_original_preview: list[dict] | None = None
            detalle_contra = dict(detalle_base)

            if not renglones_orig:
                cur.execute(
                    """
                    SELECT * FROM cuentaproveedor
                    WHERE CodigoMovimiento=%s AND COALESCE(Anulado,'No')='Si'
                    LIMIT 1
                    """,
                    (cm,),
                )
                cab_anul = cur.fetchone()
                if not cab_anul:
                    items.append(
                        {
                            "tabla": "cont_asiento",
                            "clave": {"codigo_movimiento_original": cm_str},
                            "accion": "bloqueado",
                            "valor_anterior": None,
                            "valor_nuevo": None,
                            "delta": "0",
                            "check_id": CHECK_ANULACION,
                            "referencia": "H53",
                            "excluido": True,
                            "bloqueado": True,
                            "motivo_bloqueo": "sin_asiento_original_ni_reconstruible",
                            "detalle": detalle_contra,
                        }
                    )
                    continue

                renglones_recon, meta = _reconstruir_renglones_comprobante_anulado(
                    repo, cab_anul
                )
                if not renglones_recon or meta is None:
                    items.append(
                        {
                            "tabla": "cont_asiento",
                            "clave": {"codigo_movimiento_original": cm_str},
                            "accion": "bloqueado",
                            "valor_anterior": None,
                            "valor_nuevo": None,
                            "delta": "0",
                            "check_id": CHECK_ANULACION,
                            "referencia": "H53",
                            "excluido": True,
                            "bloqueado": True,
                            "motivo_bloqueo": "sin_asiento_original_ni_reconstruible",
                            "detalle": detalle_contra,
                        }
                    )
                    continue

                regenerar_original = True
                detalle_contra["reconstruido_desde_comprobante"] = True
                id_ejercicio = meta["id_ejercicio"]
                fecha_asiento = meta["fecha_asiento"] or to_date_or_none(fecha)
                desc_asiento = meta["desc_asiento"]
                concepto_orig = meta["concepto"]
                desc_concepto_orig = meta["desc_concepto"]
                renglones_original_preview = [
                    {
                        "id_pc": r["id_pc"],
                        "debe_asiento": r["debe_asiento"],
                        "haber_asiento": r["haber_asiento"],
                        "id_concepto_asiento": concepto_orig,
                        "desc_concepto_asiento": desc_concepto_orig,
                    }
                    for r in renglones_recon
                ]
                fuente_invertir = renglones_recon
            else:
                primera = renglones_orig[0]
                id_ejercicio = to_int_or_none(
                    primera.get("id_ejercicio") if isinstance(primera, dict) else None
                )
                fecha_asiento = to_date_or_none(
                    primera.get("fecha_asiento") if isinstance(primera, dict) else None
                ) or to_date_or_none(fecha)
                desc_asiento = str_or_default(
                    primera.get("desc_asiento") if isinstance(primera, dict) else "",
                    f"Anulación - {tipo} - {nro_comp}",
                )
                fuente_invertir = renglones_orig

            id_concepto_anul = CONCEPTO_ANUL.get(tipo, 4)
            desc_concepto_anul = DESC_CONCEPTO_ANUL.get(id_concepto_anul, "Anulación")

            renglones_preview: list[dict] = []
            for r in fuente_invertir:
                debe = _r2(r.get("debe_asiento"))
                haber = _r2(r.get("haber_asiento"))
                if debe == 0 and haber == 0:
                    continue
                renglones_preview.append(
                    {
                        "id_pc": to_int_or_none(r.get("id_pc")),
                        "debe_asiento": str(_r2(haber)),
                        "haber_asiento": str(_r2(debe)),
                        "desc_renglon_asiento": MARCA_ANUL_REGEN,
                        "desc_concepto_asiento": desc_concepto_anul,
                        "id_concepto_asiento": id_concepto_anul,
                    }
                )

            if not renglones_preview:
                if regenerar_original:
                    items.append(
                        {
                            "tabla": "cont_asiento",
                            "clave": {"codigo_movimiento_original": cm_str},
                            "accion": "bloqueado",
                            "valor_anterior": None,
                            "valor_nuevo": None,
                            "delta": "0",
                            "check_id": CHECK_ANULACION,
                            "referencia": "H53",
                            "excluido": True,
                            "bloqueado": True,
                            "motivo_bloqueo": "sin_asiento_original_ni_reconstruible",
                            "detalle": detalle_contra,
                        }
                    )
                continue

            cm_estimado = repo.nro_asiento_ejercicio(id_ejercicio) if id_ejercicio else 0
            valor_nuevo: dict[str, Any] = {
                "codigo_movimiento_original": cm_str,
                "id_concepto_asiento": id_concepto_anul,
                "desc_concepto_asiento": desc_concepto_anul,
                "id_ejercicio": id_ejercicio,
                "fecha_asiento": fecha_asiento,
                "desc_asiento": desc_asiento,
                "desc_renglon_asiento": MARCA_ANUL_REGEN,
                "renglones_preview": renglones_preview,
                "nro_asiento_estimado": cm_estimado,
            }
            if regenerar_original and renglones_original_preview:
                valor_nuevo["regenerar_original"] = True
                valor_nuevo["renglones_original_preview"] = renglones_original_preview

            items.append(
                {
                    "tabla": "cont_asiento",
                    "clave": {"codigo_movimiento_original": cm_str},
                    "accion": "insert_contra_asiento",
                    "valor_anterior": None,
                    "valor_nuevo": valor_nuevo,
                    "delta": "0",
                    "check_id": CHECK_ANULACION,
                    "referencia": "H53",
                    "excluido": False,
                    "bloqueado": False,
                    "detalle": detalle_contra,
                }
            )

    return items


def _plan_concepto_anulacion_incoherente(
    repo: _RepoLectura,
    ejercicios_alcance: Optional[set[int]],
) -> list[dict]:
    """Paso REC-07(2): UPDATE de id_concepto_asiento en contra-asientos (H05)."""
    cur = repo.cur()
    sql = """
        SELECT c.codigo_movimiento,
               c.nro_asiento,
               c.id_pc,
               c.id_ejercicio,
               c.id_concepto_asiento AS concepto_contra,
               ca_orig.id_concepto_anul AS concepto_esperado,
               o.codigo_movimiento AS codigo_movimiento_original
        FROM cont_asiento o
        JOIN cont_concepto_asiento ca_orig
          ON ca_orig.id_concepto_asiento = o.id_concepto_asiento
        JOIN cont_asiento c
          ON c.codigo_movimiento_anul = o.codigo_movimiento
         AND c.id_ejercicio = o.id_ejercicio
         AND COALESCE(c.anulado, 'No') = 'No'
        WHERE COALESCE(o.anulado, 'No') = 'Si'
          AND ca_orig.id_concepto_anul IS NOT NULL
          AND c.id_concepto_asiento <> ca_orig.id_concepto_anul
    """
    params: list[Any] = []
    if ejercicios_alcance is not None:
        if not ejercicios_alcance:
            return []
        placeholders = ",".join(["%s"] * len(ejercicios_alcance))
        sql += f" AND o.id_ejercicio IN ({placeholders})"
        params.extend(sorted(ejercicios_alcance))

    cur.execute(sql, params)
    items: list[dict] = []
    for row in cur.fetchall():
        id_ej = to_int_or_none(row.get("id_ejercicio"))
        id_pc = to_int_or_none(row.get("id_pc"))
        nro_asiento = to_int_or_none(row.get("nro_asiento"))
        codmov = str_or_default(row.get("codigo_movimiento"))
        concepto_contra = to_int_or_none(row.get("concepto_contra"))
        concepto_esperado = to_int_or_none(row.get("concepto_esperado"))
        if id_ej is None or id_pc is None or nro_asiento is None or concepto_esperado is None:
            continue
        items.append(
            {
                "tabla": "cont_asiento",
                "clave": {
                    "codigo_movimiento": codmov,
                    "nro_asiento": nro_asiento,
                    "id_pc": id_pc,
                    "id_ejercicio": id_ej,
                },
                "accion": "update",
                "campo": "id_concepto_asiento",
                "valor_anterior": str(concepto_contra) if concepto_contra is not None else "",
                "valor_nuevo": str(concepto_esperado),
                "delta": str(concepto_esperado - (concepto_contra or 0)),
                "check_id": CHECK_CONCEPTO_ANUL,
                "referencia": "H05",
                "excluido": False,
                "detalle": {
                    "codigo_movimiento_original": str_or_default(
                        row.get("codigo_movimiento_original")
                    ),
                },
            }
        )
    return items


def _plan_regeneracion_asientos(
    repo: _RepoLectura,
    ejercicios_alcance: Optional[set[int]],
) -> tuple[list[dict], dict[str, int]]:
    """Genera items INSERT para cont_asiento (solo lectura en legacy)."""
    cur = repo.cur()
    cur.execute(
        """SELECT cp.* FROM cuentaproveedor cp
           JOIN sucursales s ON s.id_sucursal = cp.CodSucursal
           WHERE s.cont='Si' AND COALESCE(cp.Anulado,'No')<>'Si'
             AND cp.TipoComprobante IN ('FA','FC','OP')
             AND COALESCE(cp.CodigoMovimiento, 0) <> 0
             AND NOT EXISTS (
                 SELECT 1 FROM cont_asiento ca
                 WHERE ca.codigo_movimiento = cp.CodigoMovimiento
                   AND COALESCE(ca.codigo_movimiento, 0) <> 0
             )"""
    )
    cabs = cur.fetchall()
    items: list[dict] = []
    contadores_nro: dict[int, int] = {}
    asientos_por_tipo: dict[str, int] = defaultdict(int)

    for cab in cabs:
        tipo = str_or_default(cab.get("TipoComprobante"))
        codmov = cab["CodigoMovimiento"]
        if tipo in TIPOS_FACTURA:
            renglones, errores = reconstruir_factura(repo, cab)
            referencia = "H51"
        else:
            renglones, errores = reconstruir_op(repo, cab)
            referencia = "H52"

        if "_ERR_" in renglones or "contado_requiere_caja" in errores:
            continue

        debe = _r2(sum(v[0] for k, v in renglones.items() if k != "_ERR_"))
        haber = _r2(sum(v[1] for k, v in renglones.items() if k != "_ERR_"))
        dif = _r2(debe - haber)
        if abs(dif) > Q2:
            if abs(dif) <= UMBRAL_REDONDEO:
                if dif > 0:
                    _add_renglon(renglones, REDONDEO_PC, haber=dif)
                else:
                    _add_renglon(renglones, REDONDEO_PC, debe=-dif)
            else:
                continue

        fecha = cab.get("Fecha")
        ejercicio = repo.ejercicio_por_fecha(fecha)
        if not ejercicio:
            continue
        id_ejercicio = to_int_or_none(ejercicio["id_ejercicio"])
        if id_ejercicio is None:
            continue
        if ejercicios_alcance is not None and id_ejercicio not in ejercicios_alcance:
            continue

        if id_ejercicio not in contadores_nro:
            contadores_nro[id_ejercicio] = repo.nro_asiento_ejercicio(id_ejercicio) or 0
        nro_asiento = contadores_nro[id_ejercicio]
        contadores_nro[id_ejercicio] = nro_asiento + 1

        concepto = CONCEPTO.get(tipo, 3)
        desc_concepto = DESC_CONCEPTO.get(concepto, "Compra")
        nro_comp = cab.get("NroComprobante")
        if tipo == "OP":
            desc_asiento = f"{str_or_default(cab.get('TipoOP')).strip()} - Nro Comp. OP - {nro_comp}"
        else:
            desc_asiento = f"Compra - Nro Comp. {nro_comp}"

        fecha_norm = to_date_or_none(fecha)
        codmov_str = str_or_default(codmov)
        asientos_por_tipo[tipo] += 1

        for id_pc in sorted(k for k in renglones if k != "_ERR_"):
            vdebe, vhaber = _r2(renglones[id_pc][0]), _r2(renglones[id_pc][1])
            if vdebe == 0 and vhaber == 0:
                continue
            valor_nuevo = {
                "nro_asiento": nro_asiento,
                "fecha_asiento": fecha_norm,
                "id_ejercicio": id_ejercicio,
                "id_periodo": None,
                "codigo_movimiento": codmov_str,
                "debe_asiento": str(vdebe),
                "haber_asiento": str(vhaber),
                "id_pc": int(id_pc),
                "desc_renglon_asiento": MARCA_REGEN,
                "desc_concepto_asiento": desc_concepto,
                "id_concepto_asiento": concepto,
                "balanceado_asiento": "Si",
                "desc_asiento": desc_asiento,
                "tipo_asiento": "Proceso",
                "anulado": "No",
            }
            items.append(
                {
                    "tabla": "cont_asiento",
                    "clave": {
                        "codigo_movimiento": codmov_str,
                        "id_pc": int(id_pc),
                        "nro_asiento": nro_asiento,
                    },
                    "accion": "insert",
                    "valor_anterior": None,
                    "valor_nuevo": valor_nuevo,
                    "delta": str(_r2(vdebe - vhaber)),
                    "check_id": CHECK_REGENERACION,
                    "referencia": referencia,
                    "excluido": False,
                }
            )

    return items, dict(asientos_por_tipo)


def _plan_regeneracion_asientos_venta(
    repo: _RepoLectura,
    ejercicios_alcance: Optional[set[int]],
) -> tuple[list[dict], dict[str, int]]:
    """Items INSERT cont_asiento para FA/FB/…/REC huérfanos en cuentacliente (solo lectura)."""
    cur = repo.cur()
    tipos_sql = ", ".join(f"'{t}'" for t in TIPOS_REGENERABLES_VENTA)
    cur.execute(
        f"""SELECT cc.* FROM cuentacliente cc
           JOIN punto_venta pv ON pv.id_punto_venta = cc.id_pv
           WHERE COALESCE(pv.cont,'No')='Si'
             AND COALESCE(cc.Anulado,'No')<>'Si'
             AND cc.TipoComprobante IN ({tipos_sql})
             AND COALESCE(cc.CodigoMovimiento, 0) <> 0
             AND NOT EXISTS (
                 SELECT 1 FROM cont_asiento ca
                 WHERE ca.codigo_movimiento = cc.CodigoMovimiento
                   AND COALESCE(ca.codigo_movimiento, 0) <> 0
             )"""
    )
    cabs = cur.fetchall()
    items: list[dict] = []
    contadores_nro: dict[int, int] = {}
    asientos_por_tipo: dict[str, int] = defaultdict(int)

    for cab in cabs:
        tipo = str_or_default(cab.get("TipoComprobante"))
        codmov = cab["CodigoMovimiento"]
        if tipo == "REC":
            renglones, errores = reconstruir_rec(repo, cab)
            referencia = "H55"
            desc_asiento = f"Cobranza - Nro Comp. REC - {cab.get('NroComprobante')}"
        elif tipo in TIPOS_FACTURA_VENTA:
            renglones, errores = reconstruir_factura_venta(repo, cab)
            referencia = "H54"
            desc_asiento = f"Venta - Nro Comp. {cab.get('NroComprobante')}"
        else:
            continue

        if "_ERR_" in renglones or errores:
            # Errores bloqueantes: sin stock/caja/medios.
            bloqueantes = {
                "sin_detalle_stock",
                "contado_sin_caja",
                "rec_sin_total",
                "rec_sin_medios",
            }
            if any(e in bloqueantes or e.startswith("tipo_") for e in errores) or "_ERR_" in renglones:
                continue

        debe = _r2(sum(v[0] for k, v in renglones.items() if k != "_ERR_"))
        haber = _r2(sum(v[1] for k, v in renglones.items() if k != "_ERR_"))
        dif = _r2(debe - haber)
        if abs(dif) > Q2:
            if abs(dif) <= UMBRAL_REDONDEO:
                if dif > 0:
                    _add_renglon(renglones, REDONDEO_PC, haber=dif)
                else:
                    _add_renglon(renglones, REDONDEO_PC, debe=-dif)
            else:
                continue

        fecha = cab.get("Fecha")
        ejercicio = repo.ejercicio_por_fecha(fecha)
        if not ejercicio:
            continue
        id_ejercicio = to_int_or_none(ejercicio["id_ejercicio"])
        if id_ejercicio is None:
            continue
        if ejercicios_alcance is not None and id_ejercicio not in ejercicios_alcance:
            continue

        if id_ejercicio not in contadores_nro:
            contadores_nro[id_ejercicio] = repo.nro_asiento_ejercicio(id_ejercicio) or 0
        nro_asiento = contadores_nro[id_ejercicio]
        contadores_nro[id_ejercicio] = nro_asiento + 1

        concepto = CONCEPTO_VENTA.get(tipo, 1)
        desc_concepto = DESC_CONCEPTO_VENTA.get(concepto, "Venta")
        fecha_norm = to_date_or_none(fecha)
        codmov_str = str_or_default(codmov)
        asientos_por_tipo[tipo] += 1

        for id_pc in sorted(k for k in renglones if k != "_ERR_"):
            vdebe, vhaber = _r2(renglones[id_pc][0]), _r2(renglones[id_pc][1])
            if vdebe == 0 and vhaber == 0:
                continue
            valor_nuevo = {
                "nro_asiento": nro_asiento,
                "fecha_asiento": fecha_norm,
                "id_ejercicio": id_ejercicio,
                "id_periodo": None,
                "codigo_movimiento": codmov_str,
                "debe_asiento": str(vdebe),
                "haber_asiento": str(vhaber),
                "id_pc": int(id_pc),
                "desc_renglon_asiento": MARCA_REGEN_VENTA,
                "desc_concepto_asiento": desc_concepto,
                "id_concepto_asiento": concepto,
                "balanceado_asiento": "Si",
                "desc_asiento": desc_asiento,
                "tipo_asiento": "Proceso",
                "anulado": "No",
            }
            items.append(
                {
                    "tabla": "cont_asiento",
                    "clave": {
                        "codigo_movimiento": codmov_str,
                        "id_pc": int(id_pc),
                        "nro_asiento": nro_asiento,
                    },
                    "accion": "insert",
                    "valor_anterior": None,
                    "valor_nuevo": valor_nuevo,
                    "delta": str(_r2(vdebe - vhaber)),
                    "check_id": CHECK_REGENERACION_VENTA,
                    "referencia": referencia,
                    "excluido": False,
                }
            )

    return items, dict(asientos_por_tipo)


def _movimientos_diario(
    repo: _RepoLectura,
    asientos_simulados: list[dict],
    *,
    tratamiento_anulados: str = "incluir_neutralizado",
) -> list[dict]:
    """Filas cont_asiento (lectura) más renglones simulados del plan.

    Con ``tratamiento_anulados=incluir_neutralizado`` (default) carga todas las
    filas (original + contra se netean). Con ``excluir`` omite ``anulado='Si'``.
    """
    filtro_anul = ""
    if tratamiento_anulados != "incluir_neutralizado":
        filtro_anul = " AND COALESCE(anulado, 'No') <> 'Si'"
    cur = repo.cur()
    cur.execute(
        f"""SELECT id_pc, id_ejercicio, id_periodo,
                  COALESCE(debe_asiento,0) AS debe_asiento,
                  COALESCE(haber_asiento,0) AS haber_asiento
           FROM cont_asiento
           WHERE id_ejercicio IS NOT NULL AND id_pc IS NOT NULL{filtro_anul}"""
    )
    movs = [dict(r) for r in cur.fetchall()]
    for item in asientos_simulados:
        if item.get("excluido"):
            continue
        vn = item.get("valor_nuevo") or {}
        movs.append(
            {
                "id_pc": vn.get("id_pc"),
                "id_ejercicio": vn.get("id_ejercicio"),
                "id_periodo": vn.get("id_periodo"),
                "debe_asiento": vn.get("debe_asiento"),
                "haber_asiento": vn.get("haber_asiento"),
            }
        )
    return movs


def _saldos_derivados(repo: _RepoLectura, movimientos: list[dict]) -> dict[tuple[int, int], Decimal]:
    """Modelo sin arrastre: Σ firmada por (id_pc, id_ejercicio) sobre los movimientos dados."""
    natur: dict[int, str] = {}
    cur = repo.cur()
    cur.execute("SELECT id_pc, saldo_pc FROM cont_pc")
    for r in cur.fetchall():
        id_pc = to_int_or_none(r["id_pc"])
        if id_pc is None:
            continue
        natur[id_pc] = str_or_default(r.get("saldo_pc"), "Deudor") or "Deudor"

    # Misma precisión que el check / eliminación: Σ en precisión plena y ROUND 2 al final.
    acum: dict[tuple[int, int], Decimal] = defaultdict(lambda: Decimal("0"))
    for mov in movimientos:
        id_pc = to_int_or_none(mov.get("id_pc"))
        id_ej = to_int_or_none(mov.get("id_ejercicio"))
        if id_pc is None or id_ej is None:
            continue
        debe = _d(mov.get("debe_asiento"))
        haber = _d(mov.get("haber_asiento"))
        signo = (haber - debe) if natur.get(id_pc) == "Acreedor" else (debe - haber)
        acum[(id_pc, id_ej)] += signo

    return {k: _r2(v) for k, v in acum.items()}


def _saldos_periodo_derivados(
    repo: _RepoLectura, movimientos: list[dict]
) -> dict[tuple[int, int, int], Decimal]:
    """Σ firmada por (id_pc, id_ejercicio, id_periodo); omite id_periodo NULL."""
    natur: dict[int, str] = {}
    cur = repo.cur()
    cur.execute("SELECT id_pc, saldo_pc FROM cont_pc")
    for r in cur.fetchall():
        id_pc = to_int_or_none(r["id_pc"])
        if id_pc is None:
            continue
        natur[id_pc] = str_or_default(r.get("saldo_pc"), "Deudor") or "Deudor"

    acum: dict[tuple[int, int, int], Decimal] = defaultdict(lambda: Decimal("0"))
    for mov in movimientos:
        id_pc = to_int_or_none(mov.get("id_pc"))
        id_ej = to_int_or_none(mov.get("id_ejercicio"))
        id_per = to_int_or_none(mov.get("id_periodo"))
        if id_pc is None or id_ej is None or id_per is None:
            continue
        debe = _d(mov.get("debe_asiento"))
        haber = _d(mov.get("haber_asiento"))
        signo = (haber - debe) if natur.get(id_pc) == "Acreedor" else (debe - haber)
        acum[(id_pc, id_ej, id_per)] += signo

    return {k: _r2(v) for k, v in acum.items()}


def _tabla_existe(repo: _RepoLectura, tabla: str) -> bool:
    cur = repo.cur()
    cur.execute(
        """SELECT 1 FROM information_schema.tables
           WHERE table_schema = DATABASE() AND table_name = %s LIMIT 1""",
        (tabla,),
    )
    return cur.fetchone() is not None


def _tiene_periodos(repo: _RepoLectura) -> bool:
    if not _tabla_existe(repo, "cont_periodo"):
        return False
    cur = repo.cur()
    cur.execute("SELECT 1 FROM cont_periodo LIMIT 1")
    return cur.fetchone() is not None


def _plan_reconstruccion_saldos(
    repo: _RepoLectura,
    asientos_simulados: list[dict],
    ejercicios_alcance: Optional[set[int]],
    tolerancia: Decimal,
    *,
    tratamiento_anulados: str = "incluir_neutralizado",
) -> list[dict]:
    movimientos = _movimientos_diario(
        repo, asientos_simulados, tratamiento_anulados=tratamiento_anulados
    )
    calc = _saldos_derivados(repo, movimientos)

    cur = repo.cur()
    cur.execute(
        "SELECT id_pc, id_ejercicio, saldo_ejercicio_cta FROM cont_ejercicio_saldo_cta"
    )
    stored: dict[tuple[int, int], Decimal] = {}
    for r in cur.fetchall():
        id_pc = to_int_or_none(r["id_pc"])
        id_ej = to_int_or_none(r["id_ejercicio"])
        if id_pc is None or id_ej is None:
            continue
        stored[(id_pc, id_ej)] = _r2(r.get("saldo_ejercicio_cta"))

    items: list[dict] = []
    claves = set(calc.keys()) | set(stored.keys())

    for id_pc, id_ej in claves:
        if ejercicios_alcance is not None and id_ej not in ejercicios_alcance:
            continue
        nuevo = calc.get((id_pc, id_ej), Decimal("0"))
        anterior = stored.get((id_pc, id_ej), Decimal("0"))
        delta = _r2(nuevo - anterior)
        if repo.saldo_pc(id_pc) is None:
            continue

        # Paso REC-07(3): fila faltante → INSERT dedicado (cuentas_sin_fila_saldo).
        if (id_pc, id_ej) not in stored:
            items.append(
                {
                    "tabla": "cont_ejercicio_saldo_cta",
                    "clave": {"id_pc": id_pc, "id_ejercicio": id_ej},
                    "accion": "insert",
                    "valor_anterior": None,
                    "valor_nuevo": str(nuevo),
                    "delta": str(nuevo),
                    "check_id": CHECK_FILAS_SALDO,
                    "referencia": "H10",
                    "excluido": False,
                }
            )
            continue

        # Paso REC-07(4): recompute maestro solo UPDATE sobre filas existentes.
        if abs(delta) <= tolerancia:
            continue

        items.append(
            {
                "tabla": "cont_ejercicio_saldo_cta",
                "clave": {"id_pc": id_pc, "id_ejercicio": id_ej},
                "accion": "update",
                "valor_anterior": str(anterior),
                "valor_nuevo": str(nuevo),
                "delta": str(delta),
                "check_id": CHECK_SALDOS,
                "referencia": "H53",
                "excluido": False,
            }
        )

    if _tiene_periodos(repo) and _tabla_existe(repo, "cont_periodo_saldo_cta"):
        calc_per = _saldos_periodo_derivados(repo, movimientos)
        cur.execute(
            "SELECT id_pc, id_ejercicio, id_periodo, saldo_periodo_cta FROM cont_periodo_saldo_cta"
        )
        stored_per: dict[tuple[int, int, int], Decimal] = {}
        for r in cur.fetchall():
            id_pc = to_int_or_none(r["id_pc"])
            id_ej = to_int_or_none(r["id_ejercicio"])
            id_per = to_int_or_none(r["id_periodo"])
            if id_pc is None or id_ej is None or id_per is None:
                continue
            stored_per[(id_pc, id_ej, id_per)] = _r2(r.get("saldo_periodo_cta"))

        claves_per = set(calc_per.keys()) | set(stored_per.keys())
        for id_pc, id_ej, id_per in claves_per:
            if ejercicios_alcance is not None and id_ej not in ejercicios_alcance:
                continue
            nuevo = calc_per.get((id_pc, id_ej, id_per), Decimal("0"))
            anterior = stored_per.get((id_pc, id_ej, id_per), Decimal("0"))
            delta = _r2(nuevo - anterior)
            if repo.saldo_pc(id_pc) is None:
                continue

            if (id_pc, id_ej, id_per) not in stored_per:
                items.append(
                    {
                        "tabla": "cont_periodo_saldo_cta",
                        "clave": {
                            "id_pc": id_pc,
                            "id_ejercicio": id_ej,
                            "id_periodo": id_per,
                        },
                        "accion": "insert",
                        "valor_anterior": None,
                        "valor_nuevo": str(nuevo),
                        "delta": str(nuevo),
                        "check_id": CHECK_FILAS_SALDO,
                        "referencia": "H17",
                        "excluido": False,
                    }
                )
                continue

            if abs(delta) <= tolerancia:
                continue

            items.append(
                {
                    "tabla": "cont_periodo_saldo_cta",
                    "clave": {
                        "id_pc": id_pc,
                        "id_ejercicio": id_ej,
                        "id_periodo": id_per,
                    },
                    "accion": "update",
                    "valor_anterior": str(anterior),
                    "valor_nuevo": str(nuevo),
                    "delta": str(delta),
                    "check_id": CHECK_SALDOS_PERIODO,
                    "referencia": "H53",
                    "excluido": False,
                }
            )

    return items


def calcular_data_fingerprint(items: list[dict]) -> str:
    """SHA-256 sobre tuplas (tabla, clave, valor_actual) ordenadas."""
    tuplas: list[str] = []
    for item in sorted(items, key=lambda x: (x.get("tabla", ""), json.dumps(x.get("clave") or {}, sort_keys=True))):
        clave_canon = json.dumps(item.get("clave") or {}, sort_keys=True, separators=(",", ":"))
        valor_actual = item.get("valor_anterior")
        if valor_actual is None:
            valor_str = ""
        else:
            valor_str = str(valor_actual)
        tuplas.append(f"{item.get('tabla')}|{clave_canon}|{valor_str}")
    payload = "\n".join(tuplas)
    return "v1:" + hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _generar_backups_propuestos(timestamp: str, tablas: set[str]) -> dict[str, str]:
    return {tabla: f"{tabla}_bkp_{timestamp}" for tabla in sorted(tablas)}


def _listar_codigos_rei_cuenta(cur, id_pc: int, id_ejercicio: int) -> list[str]:
    """Identifica asientos REI vigentes de una cuenta/ejercicio (concepto 13)."""
    return listar_codigos_movimiento_rei(cur, id_pc, id_ejercicio)


def _plan_propuestas_rei(
    repo: _RepoLectura,
    id_ejercicio: int,
    tolerancia: Decimal,
    ejercicios_alcance: Optional[set[int]],
) -> list[dict]:
    """Propuestas REI por cuenta (dry-run, solo SELECT)."""
    if ejercicios_alcance is not None and id_ejercicio not in ejercicios_alcance:
        return []

    cur = repo.cur()
    evaluacion = evaluar_rei_ejercicio(cur, id_ejercicio)
    propuestas: list[dict] = []

    for cuenta in evaluacion["cuentas"]:
        codigos = _listar_codigos_rei_cuenta(cur, cuenta.id_pc, id_ejercicio)
        base = {
            "id_pc": cuenta.id_pc,
            "cod_pc": cuenta.cod_pc,
            "id_ejercicio": id_ejercicio,
            "rei_actual": str(_r2(cuenta.rei_registrado)),
            "codigos_movimiento_rei": codigos,
            "referencia": "H02",
            "excluido": False,
            "motivo_exclusion": None,
        }

        if not cuenta.computable:
            propuestas.append(
                {
                    **base,
                    "rei_teorico": None,
                    "delta": None,
                    "excluido": True,
                    "motivo_exclusion": cuenta.motivo_no_computable
                    or evaluacion.get("motivo_ind_cierre")
                    or "REI no computable",
                    "referencia": "H02",
                }
            )
            continue

        rei_teorico = _r2(cuenta.rei_teorico)
        delta = _r2(rei_teorico - cuenta.rei_registrado)
        if abs(delta) <= tolerancia:
            continue

        propuestas.append(
            {
                **base,
                "rei_teorico": str(rei_teorico),
                "delta": str(delta),
            }
        )

    for desal in evaluacion["desalineaciones"]:
        propuestas.append(
            {
                "id_pc": desal.id_pc,
                "cod_pc": desal.cod_pc,
                "id_ejercicio": id_ejercicio,
                "rei_teorico": None,
                "rei_actual": None,
                "delta": None,
                "codigos_movimiento_rei": [],
                "referencia": "H44",
                "excluido": True,
                "motivo_exclusion": desal.detalle.get("mensaje", "Desalineación de config REI"),
                "tipo_desalineacion": desal.tipo,
                "detalle_desalineacion": desal.detalle,
            }
        )

    return propuestas


def _sincronizar_aprobaciones_rei(dry_run_id, propuestas: list[dict]) -> int:
    """Persiste/actualiza ``AprobacionREI`` en estado pendiente."""
    claves_vistas: set[tuple[int, int]] = set()
    for prop in propuestas:
        id_pc = to_int_or_none(prop.get("id_pc"))
        id_ej = to_int_or_none(prop.get("id_ejercicio"))
        if id_pc is None or id_ej is None:
            continue
        claves_vistas.add((id_pc, id_ej))
        existente = AprobacionREI.objects.filter(
            dry_run_id=dry_run_id, id_pc=id_pc, id_ejercicio=id_ej
        ).first()
        defaults = {
            "rei_teorico": _d(prop.get("rei_teorico")),
            "rei_actual": _d(prop.get("rei_actual")),
        }
        if existente is None:
            AprobacionREI.objects.create(
                dry_run_id=dry_run_id,
                id_pc=id_pc,
                id_ejercicio=id_ej,
                estado="pendiente",
                **defaults,
            )
        else:
            existente.rei_teorico = defaults["rei_teorico"]
            existente.rei_actual = defaults["rei_actual"]
            if existente.estado == "pendiente":
                existente.estado = "pendiente"
            existente.save(update_fields=["rei_teorico", "rei_actual", "estado"])

    if claves_vistas:
        qs = AprobacionREI.objects.filter(dry_run_id=dry_run_id, estado="pendiente")
        for obj in qs:
            if (obj.id_pc, obj.id_ejercicio) not in claves_vistas:
                obj.delete()
    else:
        AprobacionREI.objects.filter(dry_run_id=dry_run_id, estado="pendiente").delete()
    return AprobacionREI.objects.filter(dry_run_id=dry_run_id).count()


def _check_ids_alcance(alcance: dict) -> set[str]:
    raw = alcance.get("check_ids") or []
    if isinstance(raw, str):
        raw = [raw]
    return {str(cid) for cid in raw if cid}


def _calcular_impacto(
    items: list[dict],
    asientos_por_tipo: dict[str, int],
    propuestas_rei: Optional[list[dict]] = None,
    checks_incluidos: Optional[list[str]] = None,
) -> dict[str, Any]:
    totales_tabla: dict[str, int] = defaultdict(int)
    cuentas_delta: dict[int, Decimal] = defaultdict(lambda: Decimal("0"))
    aplicables = 0

    for item in items:
        totales_tabla[item["tabla"]] += 1
        if item.get("excluido"):
            continue
        aplicables += 1
        if item["tabla"] == "cont_ejercicio_saldo_cta":
            id_pc = to_int_or_none((item.get("clave") or {}).get("id_pc"))
            delta = to_decimal_or_none(item.get("delta"))
            if id_pc is not None and delta is not None:
                cuentas_delta[id_pc] += delta

    cuentas_impactadas = [
        {"id_pc": id_pc, "delta_total": str(_r2(delta))}
        for id_pc, delta in sorted(cuentas_delta.items(), key=lambda x: abs(x[1]), reverse=True)
    ]

    propuestas_rei = propuestas_rei or []
    anulaciones_bloqueadas = sum(
        1
        for item in items
        if item.get("check_id") == CHECK_ANULACION and item.get("bloqueado")
    )
    anulaciones_reparables = sum(
        1
        for item in items
        if item.get("check_id") == CHECK_ANULACION and not item.get("bloqueado") and not item.get("excluido")
    )
    return {
        "totales_por_tabla": dict(totales_tabla),
        "total_items": len(items),
        "total_aplicables": aplicables,
        "total_excluidos": len(items) - aplicables,
        "asientos_regenerar_por_tipo": asientos_por_tipo,
        "cuentas_impactadas": cuentas_impactadas,
        "checks_incluidos": list(checks_incluidos or CHECKS_INCLUIDOS),
        "propuestas_rei_total": len(propuestas_rei),
        "propuestas_rei_pendientes": len(propuestas_rei),
        "anulaciones_bloqueadas": anulaciones_bloqueadas,
        "anulaciones_reparables": anulaciones_reparables,
    }


def dry_run(
    base_empresa: str,
    alcance: dict,
    politica: dict,
    usuario: str = "",
    dry_run_id=None,
) -> dict[str, Any]:
    """
    Ejecuta dry-run de corrección (100 % SELECT en legacy).

    Genera plan de items, persiste ``PlanCorreccion`` en Postgres y devuelve
    payload con guards (TTL, config_hash, data_fingerprint) e impacto.

    Si ``dry_run_id`` está seteado, actualiza in-place el plan existente
    (mismo UUID): recalcula plan, hashes y ``expira_en``, mantiene ``creado_en``
    y ``dry_run_id``. Solo permitido si ``estado == "propuesto"`` y no expirado.
    """
    if not base_empresa:
        raise ValueError("base_empresa es obligatorio.")
    if not alcance.get("id_ejercicio") and politica.get("alcance_recompute") == "ejercicio_seleccionado":
        raise ValueError("id_ejercicio es obligatorio en el alcance.")

    check_ids = _check_ids_alcance(alcance)
    if not check_ids:
        raise ValueError("Seleccioná al menos un diagnóstico.")

    config_hash = calcular_config_hash(politica)
    tolerancia = _d(politica.get("tolerancia_decimal", Decimal("0.005")))
    ahora = timezone.now()
    expira = ahora + timedelta(minutes=PLAN_TTL_MIN)

    checks_planificados: list[str] = []

    pool = get_mysql_pool()
    with pool.get_connection(base_empresa) as conn:
        repo = _RepoLectura(conn)
        ejercicios_alcance = _ejercicios_en_alcance(alcance, politica, repo)

        items_concepto: list[dict] = []
        if CHECK_CONCEPTO_ANUL in check_ids:
            checks_planificados.append(CHECK_CONCEPTO_ANUL)
            items_concepto = _plan_concepto_anulacion_incoherente(repo, ejercicios_alcance)

        items_asientos: list[dict] = []
        asientos_por_tipo: dict[str, int] = {}
        if CHECK_REGENERACION in check_ids:
            checks_planificados.append(CHECK_REGENERACION)
            items_asientos, asientos_por_tipo = _plan_regeneracion_asientos(repo, ejercicios_alcance)

        items_asientos_venta: list[dict] = []
        if CHECK_REGENERACION_VENTA in check_ids:
            checks_planificados.append(CHECK_REGENERACION_VENTA)
            items_asientos_venta, asientos_venta_por_tipo = _plan_regeneracion_asientos_venta(
                repo, ejercicios_alcance
            )
            for tipo, cant in asientos_venta_por_tipo.items():
                asientos_por_tipo[tipo] = asientos_por_tipo.get(tipo, 0) + cant

        items_asientos_todos = items_asientos + items_asientos_venta

        items_anulacion: list[dict] = []
        if CHECK_ANULACION in check_ids:
            checks_planificados.append(CHECK_ANULACION)
            items_anulacion = _plan_reparacion_anulaciones(conn, repo, politica, alcance)

        incluir_saldos = bool(check_ids & CHECKS_SALDOS) or bool(
            check_ids & CHECKS_REGENERACION_ASIENTO
        )
        items_saldos: list[dict] = []
        if incluir_saldos:
            if check_ids & CHECKS_SALDOS:
                checks_planificados.extend(
                    [cid for cid in CHECKS_INCLUIDOS if cid in check_ids and cid in CHECKS_SALDOS]
                )
            elif check_ids & CHECKS_REGENERACION_ASIENTO:
                checks_planificados.extend(
                    [CHECK_FILAS_SALDO, CHECK_SALDOS, CHECK_SALDOS_PERIODO]
                )
            items_saldos = _plan_reconstruccion_saldos(
                repo,
                items_asientos_todos,
                ejercicios_alcance,
                tolerancia,
                tratamiento_anulados=politica.get("tratamiento_anulados", "incluir_neutralizado"),
            )

        items = items_asientos_todos + items_anulacion + items_concepto + items_saldos
        _marcar_exclusiones(items, politica, repo)
        data_fingerprint = _calcular_fingerprint_desde_legacy(
            conn, _filtrar_items_aplicables(items)
        )

        id_ejercicio = to_int_or_none(alcance.get("id_ejercicio"))
        propuestas_rei: list[dict] = []
        if CHECK_REI in check_ids and id_ejercicio is not None:
            checks_planificados.append(CHECK_REI)
            propuestas_rei = _plan_propuestas_rei(
                repo, id_ejercicio, tolerancia, ejercicios_alcance
            )

    checks_incluidos = list(dict.fromkeys(checks_planificados))

    backups_propuestos: dict[str, str] = {}
    impacto = _calcular_impacto(
        items,
        asientos_por_tipo,
        propuestas_rei,
        checks_incluidos=checks_incluidos,
    )

    plan_json = {
        "items": items,
        "items_anulacion": items_anulacion,
        "backups_propuestos": backups_propuestos,
        "impacto": impacto,
        "checks_incluidos": checks_incluidos,
        "propuestas_rei": propuestas_rei,
    }

    if dry_run_id:
        try:
            plan_obj = PlanCorreccion.objects.get(dry_run_id=dry_run_id)
        except PlanCorreccion.DoesNotExist as exc:
            raise ValueError(
                "No existe un plan de diagnóstico con ese identificador."
            ) from exc
        if plan_obj.base_empresa != base_empresa:
            raise ValueError("El plan no corresponde a la empresa indicada.")
        if plan_obj.estado != "propuesto":
            raise ValueError(
                f"El plan está en estado «{plan_obj.estado}» y no puede actualizarse."
            )
        if plan_obj.expira_en and plan_obj.expira_en <= ahora:
            raise ValueError(
                "El plan de diagnóstico expiró. Generá uno nuevo desde el tablero."
            )
        plan_obj.alcance = dict(alcance)
        plan_obj.config_hash = config_hash
        plan_obj.data_fingerprint = data_fingerprint
        plan_obj.plan = plan_json
        plan_obj.estado = "propuesto"
        plan_obj.creado_por = usuario or "sistema"
        plan_obj.expira_en = expira
        plan_obj.save(
            update_fields=[
                "alcance",
                "config_hash",
                "data_fingerprint",
                "plan",
                "estado",
                "creado_por",
                "expira_en",
            ]
        )
    else:
        plan_obj = PlanCorreccion.objects.create(
            base_empresa=base_empresa,
            alcance=dict(alcance),
            config_hash=config_hash,
            data_fingerprint=data_fingerprint,
            plan=plan_json,
            estado="propuesto",
            creado_por=usuario or "sistema",
            creado_en=ahora,
            expira_en=expira,
        )

    total_rei = _sincronizar_aprobaciones_rei(plan_obj.dry_run_id, propuestas_rei)
    impacto["propuestas_rei_total"] = total_rei
    impacto["propuestas_rei_pendientes"] = AprobacionREI.objects.filter(
        dry_run_id=plan_obj.dry_run_id, estado="pendiente"
    ).count()
    plan_json["impacto"] = impacto
    plan_obj.plan = plan_json
    plan_obj.save(update_fields=["plan"])

    return {
        "dry_run_id": str(plan_obj.dry_run_id),
        "base_empresa": base_empresa,
        "alcance": dict(alcance),
        "config_hash": config_hash,
        "data_fingerprint": data_fingerprint,
        "estado": plan_obj.estado,
        "creado_por": plan_obj.creado_por,
        "creado_en": _fecha_ui(plan_obj.creado_en),
        "expira_en": _fecha_ui(plan_obj.expira_en),
        "guards": {
            "ttl_minutos": PLAN_TTL_MIN,
            "config_hash": config_hash,
            "data_fingerprint": data_fingerprint,
            "expira_en": _fecha_ui(plan_obj.expira_en),
        },
        "plan": plan_json,
        "impacto": impacto,
        "backups_propuestos": backups_propuestos,
        "propuestas_rei": propuestas_rei,
        "propuestas_rei_total": total_rei,
        "rei_aprobacion_url_hint": (
            f"/contabilidad/auditoria/rei/{plan_obj.dry_run_id}/"
            if propuestas_rei
            else None
        ),
    }


class CorreccionContableError(Exception):
    """Error controlado del motor de corrección Fase 3."""


def _filtrar_items_aplicables(items: list[dict]) -> list[dict]:
    aplicables: list[dict] = []
    for item in items:
        if item.get("excluido"):
            continue
        if item.get("bloqueado"):
            continue
        if item.get("check_id") in CHECKS_EXCLUIDOS_AUTO_APPLY:
            continue
        aplicables.append(item)
    return aplicables


def _asiento_ya_existe(cur, codigo_movimiento) -> bool:
    cm = str_or_default(codigo_movimiento)
    if not cm or cm == "0":
        return False
    cur.execute(
        """SELECT 1 FROM cont_asiento
           WHERE codigo_movimiento=%s AND COALESCE(codigo_movimiento,0)<>0 LIMIT 1""",
        (cm,),
    )
    return cur.fetchone() is not None


def _leer_valor_actual_item(cur, item: dict) -> Optional[str]:
    """Valor actual legacy para re-validación de fingerprint."""
    tabla = item.get("tabla")
    clave = item.get("clave") or {}
    accion = item.get("accion", "update")

    if tabla == "cont_asiento" and accion == "insert":
        codmov = clave.get("codigo_movimiento")
        if _asiento_ya_existe(cur, codmov):
            return "EXISTE"
        return ""

    if tabla == "cont_asiento" and accion == "update":
        codmov = str_or_default(clave.get("codigo_movimiento"))
        nro_asiento = to_int_or_none(clave.get("nro_asiento"))
        id_pc = to_int_or_none(clave.get("id_pc"))
        if not codmov or nro_asiento is None or id_pc is None:
            return None
        cur.execute(
            """SELECT id_concepto_asiento FROM cont_asiento
               WHERE codigo_movimiento=%s AND nro_asiento=%s AND id_pc=%s""",
            (codmov, nro_asiento, id_pc),
        )
        row = cur.fetchone()
        if not row:
            return None
        concepto = to_int_or_none(row.get("id_concepto_asiento") if isinstance(row, dict) else row[0])
        return str(concepto) if concepto is not None else ""

    if item.get("check_id") == CHECK_ANULACION:
        if accion == "insert_marcador":
            cm_anul = clave.get("codigo_movimiento_anul") or clave.get("codigo_movimiento_original")
            cur.execute(
                """SELECT 1 FROM cuentaproveedor
                   WHERE CodigoMovimiento=0 AND codigo_movimiento_anul=%s LIMIT 1""",
                (cm_anul,),
            )
            return "EXISTE" if cur.fetchone() else ""
        if accion == "marcar_original_anulado":
            codmov = str_or_default(clave.get("codigo_movimiento"))
            cur.execute(
                """SELECT COUNT(*) AS cnt FROM cont_asiento
                   WHERE codigo_movimiento=%s AND COALESCE(anulado,'No')<>'Si'""",
                (codmov,),
            )
            row = cur.fetchone()
            pendientes = row.get("cnt") if isinstance(row, dict) else row[0]
            return "Si" if (pendientes or 0) == 0 else "No"
        if accion == "insert_contra_asiento":
            cm_orig = clave.get("codigo_movimiento_original")
            cur.execute(
                """SELECT 1 FROM cont_asiento
                   WHERE codigo_movimiento_anul=%s
                     AND id_concepto_asiento IN (4, 8)
                     AND COALESCE(anulado,'No')='No'
                     AND COALESCE(codigo_movimiento,0)<>0
                   LIMIT 1""",
                (cm_orig,),
            )
            return "EXISTE" if cur.fetchone() else ""

    if tabla == "cont_ejercicio_saldo_cta":
        id_pc = to_int_or_none(clave.get("id_pc"))
        id_ej = to_int_or_none(clave.get("id_ejercicio"))
        if id_pc is None or id_ej is None:
            return None
        cur.execute(
            "SELECT saldo_ejercicio_cta FROM cont_ejercicio_saldo_cta WHERE id_pc=%s AND id_ejercicio=%s",
            (id_pc, id_ej),
        )
        row = cur.fetchone()
        if row:
            if accion == "insert":
                return "EXISTE"
            return str(_r2(row.get("saldo_ejercicio_cta") if isinstance(row, dict) else row[0]))
        if accion == "insert":
            return ""
        return str(Decimal("0"))

    if tabla == "cont_periodo_saldo_cta":
        id_pc = to_int_or_none(clave.get("id_pc"))
        id_ej = to_int_or_none(clave.get("id_ejercicio"))
        id_per = to_int_or_none(clave.get("id_periodo"))
        if id_pc is None or id_ej is None or id_per is None:
            return None
        cur.execute(
            """SELECT saldo_periodo_cta FROM cont_periodo_saldo_cta
               WHERE id_pc=%s AND id_ejercicio=%s AND id_periodo=%s""",
            (id_pc, id_ej, id_per),
        )
        row = cur.fetchone()
        if row:
            if accion == "insert":
                return "EXISTE"
            return str(_r2(row.get("saldo_periodo_cta") if isinstance(row, dict) else row[0]))
        if accion == "insert":
            return ""
        return str(Decimal("0"))

    return item.get("valor_anterior")


def _calcular_fingerprint_desde_legacy(conn, items: list[dict]) -> str:
    cur = conn.cursor(MySQLdb.cursors.DictCursor)
    items_fp: list[dict] = []
    for item in items:
        valor = _leer_valor_actual_item(cur, item)
        if valor == "EXISTE":
            continue
        items_fp.append({**item, "valor_anterior": valor})
    return calcular_data_fingerprint(items_fp)


def _orden_apply_items(items: list[dict]) -> list[dict]:
    """Orden seguro REC-07: regen → anulación(1.5) → concepto(2) → filas saldo(3) → recompute(4)."""

    def _prioridad_accion_anulacion(accion: str) -> int:
        return {
            "insert_marcador": 1,
            "marcar_original_anulado": 2,
            "insert_contra_asiento": 3,
        }.get(accion, 99)

    def _prioridad(item: dict) -> tuple:
        check = item.get("check_id", "")
        accion = item.get("accion", "update")
        if check in CHECKS_REGENERACION_ASIENTO and accion == "insert":
            paso = 10
        elif check == CHECK_ANULACION:
            paso = 15
        elif check == CHECK_CONCEPTO_ANUL:
            paso = 20
        elif check == CHECK_FILAS_SALDO:
            paso = 30
        elif check in (CHECK_SALDOS, CHECK_SALDOS_PERIODO):
            paso = 40
        else:
            paso = 99
        sub = _prioridad_accion_anulacion(accion) if check == CHECK_ANULACION else 0
        return (
            paso,
            sub,
            item.get("tabla", ""),
            json.dumps(item.get("clave") or {}, sort_keys=True),
        )

    return sorted(items, key=_prioridad)


def _crear_backups(conn, tablas: set[str], timestamp: str) -> dict[str, str]:
    backups: dict[str, str] = {}
    cur = conn.cursor()
    for tabla in sorted(tablas):
        if tabla not in TABLAS_BACKUP_PERMITIDAS:
            raise CorreccionContableError(f"Tabla no permitida para backup: {tabla}")
        bkp = f"{tabla}_bkp_{timestamp}"
        cur.execute(f"CREATE TABLE `{bkp}` AS SELECT * FROM `{tabla}`")
        backups[tabla] = bkp
    conn.commit()
    return backups


def _saldo_inicial_ejercicio(cur, id_pc: int, id_ejercicio: int) -> Decimal:
    cur.execute(
        "SELECT saldo_ejercicio_cta FROM cont_ejercicio_saldo_cta WHERE id_pc=%s AND id_ejercicio=%s",
        (id_pc, id_ejercicio),
    )
    row = cur.fetchone()
    return _r2(row[0]) if row else Decimal("0")


def _insertar_log_detalle(
    cur,
    lote_id: str,
    item: dict,
    valor_anterior: Optional[str],
    valor_nuevo: Optional[str],
    usuario: str,
    fecha_db,
) -> None:
    cur.execute(
        """INSERT INTO cont_audit_correccion
           (lote_id, check_id, tabla, clave, valor_anterior, valor_nuevo, usuario, fecha)
           VALUES (%s,%s,%s,%s,%s,%s,%s,%s)""",
        (
            lote_id,
            str_or_default(item.get("check_id")),
            str_or_default(item.get("tabla")),
            json.dumps(item.get("clave") or {}, sort_keys=True, ensure_ascii=False),
            valor_anterior,
            valor_nuevo,
            usuario,
            fecha_db,
        ),
    )


def _bloquear_filas_objetivo(cur, items: list[dict]) -> None:
    ejercicios: set[int] = set()
    saldos_ej: set[tuple[int, int]] = set()
    saldos_per: set[tuple[int, int, int]] = set()
    asientos_update: set[tuple[str, int, int]] = set()
    asientos_cm_anul: set[str] = set()
    cuentaproveedor_cm: set[str] = set()

    for item in items:
        clave = item.get("clave") or {}
        tabla = item.get("tabla")
        accion = item.get("accion", "update")
        if item.get("check_id") == CHECK_ANULACION and accion == "insert_marcador":
            cm = str_or_default(clave.get("codigo_movimiento_anul") or clave.get("codigo_movimiento_original"))
            if cm:
                cuentaproveedor_cm.add(cm)
        elif item.get("check_id") == CHECK_ANULACION and accion == "marcar_original_anulado":
            cm = str_or_default(clave.get("codigo_movimiento"))
            if cm:
                asientos_cm_anul.add(cm)
        elif item.get("check_id") == CHECK_ANULACION and accion == "insert_contra_asiento":
            id_ej = to_int_or_none((item.get("valor_nuevo") or {}).get("id_ejercicio"))
            if id_ej is not None:
                ejercicios.add(id_ej)
        elif tabla == "cont_asiento" and accion == "update":
            codmov = str_or_default(clave.get("codigo_movimiento"))
            nro = to_int_or_none(clave.get("nro_asiento"))
            id_pc = to_int_or_none(clave.get("id_pc"))
            if codmov and nro is not None and id_pc is not None:
                asientos_update.add((codmov, nro, id_pc))
        elif tabla == "cont_asiento":
            id_ej = to_int_or_none((item.get("valor_nuevo") or {}).get("id_ejercicio"))
            if id_ej is not None:
                ejercicios.add(id_ej)
        elif tabla == "cont_ejercicio_saldo_cta":
            id_pc = to_int_or_none(clave.get("id_pc"))
            id_ej = to_int_or_none(clave.get("id_ejercicio"))
            if id_pc is not None and id_ej is not None:
                saldos_ej.add((id_pc, id_ej))
        elif tabla == "cont_periodo_saldo_cta":
            id_pc = to_int_or_none(clave.get("id_pc"))
            id_ej = to_int_or_none(clave.get("id_ejercicio"))
            id_per = to_int_or_none(clave.get("id_periodo"))
            if id_pc is not None and id_ej is not None and id_per is not None:
                saldos_per.add((id_pc, id_ej, id_per))

    for codmov, nro, id_pc in sorted(asientos_update):
        cur.execute(
            """SELECT id_concepto_asiento FROM cont_asiento
               WHERE codigo_movimiento=%s AND nro_asiento=%s AND id_pc=%s FOR UPDATE""",
            (codmov, nro, id_pc),
        )
    for cm in sorted(asientos_cm_anul):
        cur.execute(
            """SELECT codigo_movimiento FROM cont_asiento
               WHERE codigo_movimiento=%s LIMIT 1 FOR UPDATE""",
            (cm,),
        )
    for cm in sorted(cuentaproveedor_cm):
        cur.execute(
            """SELECT CodigoMovimiento FROM cuentaproveedor
               WHERE CodigoMovimiento=%s LIMIT 1 FOR UPDATE""",
            (cm,),
        )
    for id_ej in sorted(ejercicios):
        cur.execute(
            "SELECT nro_asiento_ejercicio FROM cont_ejercicio WHERE id_ejercicio=%s FOR UPDATE",
            (id_ej,),
        )
    for id_pc, id_ej in sorted(saldos_ej):
        cur.execute(
            """SELECT saldo_ejercicio_cta FROM cont_ejercicio_saldo_cta
               WHERE id_pc=%s AND id_ejercicio=%s FOR UPDATE""",
            (id_pc, id_ej),
        )
    for id_pc, id_ej, id_per in sorted(saldos_per):
        cur.execute(
            """SELECT saldo_periodo_cta FROM cont_periodo_saldo_cta
               WHERE id_pc=%s AND id_ejercicio=%s AND id_periodo=%s FOR UPDATE""",
            (id_pc, id_ej, id_per),
        )


def _aplicar_renglon_asiento(
    cur,
    repo: _RepoLectura,
    item: dict,
    nro_asiento: int,
    saldos_run: dict[tuple[int, int], Decimal],
    lote_id: str,
    usuario: str,
    fecha_db,
) -> None:
    vn = item.get("valor_nuevo") or {}
    id_ejercicio = to_int_or_none(vn.get("id_ejercicio"))
    id_pc = to_int_or_none(vn.get("id_pc"))
    vdebe = _r2(vn.get("debe_asiento"))
    vhaber = _r2(vn.get("haber_asiento"))
    if vdebe == 0 and vhaber == 0:
        return

    natur = repo.saldo_pc(id_pc) or "Deudor"
    clave_saldo = (id_pc, id_ejercicio)
    if clave_saldo not in saldos_run:
        saldos_run[clave_saldo] = _saldo_inicial_ejercicio(cur, id_pc, id_ejercicio)
    if natur == "Acreedor":
        saldos_run[clave_saldo] += vhaber - vdebe
    else:
        saldos_run[clave_saldo] += vdebe - vhaber
    saldo_asiento = _r2(saldos_run[clave_saldo])

    fecha = to_date_or_none(vn.get("fecha_asiento"))
    codmov = vn.get("codigo_movimiento")
    cur.execute(
        """INSERT INTO cont_asiento
           (nro_asiento, fecha_asiento, id_ejercicio, id_periodo,
            codigo_movimiento, debe_asiento, haber_asiento, saldo_asiento,
            id_pc, desc_renglon_asiento, desc_concepto_asiento,
            id_concepto_asiento, balanceado_asiento, id_usuario,
            desc_asiento, tipo_asiento, anulado)
           VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,'Si',NULL,%s,'Proceso','No')""",
        (
            nro_asiento,
            fecha,
            id_ejercicio,
            to_int_or_none(vn.get("id_periodo")),
            str_or_default(codmov),
            str(vdebe),
            str(vhaber),
            str(saldo_asiento),
            id_pc,
            str_or_default(vn.get("desc_renglon_asiento"), MARCA_REGEN),
            str_or_default(vn.get("desc_concepto_asiento")),
            to_int_or_none(vn.get("id_concepto_asiento")),
            str_or_default(vn.get("desc_asiento")),
        ),
    )

    valor_nuevo_log = json.dumps(
        {**vn, "nro_asiento": nro_asiento, "saldo_asiento": str(saldo_asiento)},
        sort_keys=True,
        ensure_ascii=False,
        default=str,
    )
    _insertar_log_detalle(cur, lote_id, item, None, valor_nuevo_log, usuario, fecha_db)


def _aplicar_asiento_completo(
    cur,
    repo: _RepoLectura,
    renglones: list[dict],
    saldos_run: dict[tuple[int, int], Decimal],
    lote_id: str,
    usuario: str,
    fecha_db,
) -> int:
    """Inserta todos los renglones de un comprobante; retorna cantidad insertada."""
    if not renglones:
        return 0
    vn0 = renglones[0].get("valor_nuevo") or {}
    codmov = vn0.get("codigo_movimiento")
    if _asiento_ya_existe(cur, codmov):
        return 0

    id_ejercicio = to_int_or_none(vn0.get("id_ejercicio"))
    if id_ejercicio is None:
        raise CorreccionContableError("Asiento sin id_ejercicio en el plan.")

    cur.execute(
        "SELECT nro_asiento_ejercicio FROM cont_ejercicio WHERE id_ejercicio=%s FOR UPDATE",
        (id_ejercicio,),
    )
    row = cur.fetchone()
    if not row:
        raise CorreccionContableError(f"Ejercicio {id_ejercicio} inexistente.")
    nro_asiento = to_int_or_none(row[0]) or 0
    cur.execute(
        "UPDATE cont_ejercicio SET nro_asiento_ejercicio=%s WHERE id_ejercicio=%s",
        (nro_asiento + 1, id_ejercicio),
    )

    insertados = 0
    for item in renglones:
        _aplicar_renglon_asiento(
            cur, repo, item, nro_asiento, saldos_run, lote_id, usuario, fecha_db
        )
        insertados += 1
    return insertados


def _fila_saldo_existe(cur, item: dict) -> bool:
    """Idempotencia paso 3: no duplicar INSERT si la fila ya existe."""
    clave = item.get("clave") or {}
    tabla = item.get("tabla")
    if tabla == "cont_ejercicio_saldo_cta":
        id_pc = to_int_or_none(clave.get("id_pc"))
        id_ej = to_int_or_none(clave.get("id_ejercicio"))
        if id_pc is None or id_ej is None:
            return False
        cur.execute(
            "SELECT 1 FROM cont_ejercicio_saldo_cta WHERE id_pc=%s AND id_ejercicio=%s LIMIT 1",
            (id_pc, id_ej),
        )
        return cur.fetchone() is not None
    if tabla == "cont_periodo_saldo_cta":
        id_pc = to_int_or_none(clave.get("id_pc"))
        id_ej = to_int_or_none(clave.get("id_ejercicio"))
        id_per = to_int_or_none(clave.get("id_periodo"))
        if id_pc is None or id_ej is None or id_per is None:
            return False
        cur.execute(
            """SELECT 1 FROM cont_periodo_saldo_cta
               WHERE id_pc=%s AND id_ejercicio=%s AND id_periodo=%s LIMIT 1""",
            (id_pc, id_ej, id_per),
        )
        return cur.fetchone() is not None
    return False


def _aplicar_item_concepto(
    cur,
    item: dict,
    lote_id: str,
    usuario: str,
    fecha_db,
) -> None:
    """Paso REC-07(2): UPDATE id_concepto_asiento con re-validación de concurrencia."""
    clave = item.get("clave") or {}
    codmov = str_or_default(clave.get("codigo_movimiento"))
    nro_asiento = to_int_or_none(clave.get("nro_asiento"))
    id_pc = to_int_or_none(clave.get("id_pc"))
    valor_anterior = str_or_default(item.get("valor_anterior"))
    valor_nuevo = to_int_or_none(item.get("valor_nuevo"))
    if not codmov or nro_asiento is None or id_pc is None or valor_nuevo is None:
        raise CorreccionContableError("Item de concepto anulación incompleto en el plan.")

    cur.execute(
        """SELECT id_concepto_asiento FROM cont_asiento
           WHERE codigo_movimiento=%s AND nro_asiento=%s AND id_pc=%s FOR UPDATE""",
        (codmov, nro_asiento, id_pc),
    )
    row = cur.fetchone()
    if not row:
        raise CorreccionContableError(
            f"Concurrencia: no existe el renglón cont_asiento ({codmov}, {nro_asiento}, {id_pc})."
        )
    actual = to_int_or_none(row[0] if not isinstance(row, dict) else row.get("id_concepto_asiento"))
    actual_str = str(actual) if actual is not None else ""
    if actual_str != valor_anterior:
        raise CorreccionContableError(
            f"Concurrencia en concepto anulación ({codmov}, nro {nro_asiento}, id_pc {id_pc}): "
            f"valor actual {actual_str} difiere del plan ({valor_anterior})."
        )

    cur.execute(
        """UPDATE cont_asiento SET id_concepto_asiento=%s
           WHERE codigo_movimiento=%s AND nro_asiento=%s AND id_pc=%s""",
        (valor_nuevo, codmov, nro_asiento, id_pc),
    )
    _insertar_log_detalle(
        cur,
        lote_id,
        item,
        valor_anterior,
        str(valor_nuevo),
        usuario,
        fecha_db,
    )


def _aplicar_item_saldo(
    cur,
    item: dict,
    lote_id: str,
    usuario: str,
    fecha_db,
) -> None:
    clave = item.get("clave") or {}
    vn = item.get("valor_nuevo")
    valor_nuevo = str(vn) if not isinstance(vn, dict) else str(_r2(vn))
    valor_anterior = str_or_default(item.get("valor_anterior"))
    accion = item.get("accion", "update")
    tabla = item.get("tabla")

    if tabla == "cont_ejercicio_saldo_cta":
        id_pc = to_int_or_none(clave.get("id_pc"))
        id_ej = to_int_or_none(clave.get("id_ejercicio"))
        if accion == "insert":
            cur.execute(
                "INSERT INTO cont_ejercicio_saldo_cta (id_pc, id_ejercicio, saldo_ejercicio_cta) VALUES (%s,%s,%s)",
                (id_pc, id_ej, valor_nuevo),
            )
        else:
            cur.execute(
                "UPDATE cont_ejercicio_saldo_cta SET saldo_ejercicio_cta=%s WHERE id_pc=%s AND id_ejercicio=%s",
                (valor_nuevo, id_pc, id_ej),
            )
    elif tabla == "cont_periodo_saldo_cta":
        id_pc = to_int_or_none(clave.get("id_pc"))
        id_ej = to_int_or_none(clave.get("id_ejercicio"))
        id_per = to_int_or_none(clave.get("id_periodo"))
        if accion == "insert":
            cur.execute(
                """INSERT INTO cont_periodo_saldo_cta
                   (id_pc, id_ejercicio, id_periodo, saldo_periodo_cta) VALUES (%s,%s,%s,%s)""",
                (id_pc, id_ej, id_per, valor_nuevo),
            )
        else:
            cur.execute(
                """UPDATE cont_periodo_saldo_cta SET saldo_periodo_cta=%s
                   WHERE id_pc=%s AND id_ejercicio=%s AND id_periodo=%s""",
                (valor_nuevo, id_pc, id_ej, id_per),
            )
    else:
        raise CorreccionContableError(f"Tabla de saldo no soportada: {tabla}")

    _insertar_log_detalle(cur, lote_id, item, valor_anterior, valor_nuevo, usuario, fecha_db)


def _aplicar_insert_marcador_anulacion(
    cur,
    dict_cur,
    item: dict,
    lote_id: str,
    usuario: str,
    fecha_db,
) -> int:
    clave = item.get("clave") or {}
    cm_orig = clave.get("codigo_movimiento_anul") or clave.get("codigo_movimiento_original")
    vn = item.get("valor_nuevo") or {}

    dict_cur.execute(
        """SELECT 1 FROM cuentaproveedor
           WHERE CodigoMovimiento=0 AND codigo_movimiento_anul=%s LIMIT 1""",
        (cm_orig,),
    )
    if dict_cur.fetchone():
        return 0

    dict_cur.execute(
        """SELECT * FROM cuentaproveedor
           WHERE CodigoMovimiento=%s AND COALESCE(Anulado,'No')='Si' LIMIT 1 FOR UPDATE""",
        (cm_orig,),
    )
    orig = dict_cur.fetchone()
    if not orig:
        raise CorreccionContableError(
            f"No existe comprobante original anulado con CodigoMovimiento={cm_orig}."
        )

    dict_cur.execute("SELECT COALESCE(MAX(id_cuentaproveedor),0)+1 AS nid FROM cuentaproveedor")
    row_id = dict_cur.fetchone()
    new_id = to_int_or_none(row_id.get("nid") if isinstance(row_id, dict) else row_id[0])
    if new_id is None:
        raise CorreccionContableError("No se pudo reservar id_cuentaproveedor para marcador.")

    fila = dict(orig)
    fila["id_cuentaproveedor"] = new_id
    fila["CodigoMovimiento"] = 0
    fila["codigo_movimiento_anul"] = cm_orig
    fila["Detalle"] = str_or_default(
        vn.get("Detalle"),
        f"Anulacion - {fila.get('TipoComprobante')} - {fila.get('NroComprobante')}",
    )
    fila["Anulado"] = "No"

    columnas = list(fila.keys())
    placeholders = ",".join(["%s"] * len(columnas))
    cols_sql = ",".join(f"`{c}`" for c in columnas)
    cur.execute(
        f"INSERT INTO cuentaproveedor ({cols_sql}) VALUES ({placeholders})",
        tuple(fila[c] for c in columnas),
    )
    _insertar_log_detalle(cur, lote_id, item, None, str(new_id), usuario, fecha_db)
    return 1


def _aplicar_marcar_original_anulado(
    cur,
    dict_cur,
    item: dict,
    lote_id: str,
    usuario: str,
    fecha_db,
) -> int:
    clave = item.get("clave") or {}
    codmov = str_or_default(clave.get("codigo_movimiento"))
    valor_anterior = str_or_default(item.get("valor_anterior"), "No")

    dict_cur.execute(
        """SELECT COUNT(*) AS cnt FROM cont_asiento
           WHERE codigo_movimiento=%s AND COALESCE(anulado,'No')<>'Si'""",
        (codmov,),
    )
    row = dict_cur.fetchone()
    pendientes = to_int_or_none(row.get("cnt") if isinstance(row, dict) else row[0]) or 0
    if pendientes == 0:
        return 0

    cur.execute(
        """UPDATE cont_asiento SET anulado='Si'
           WHERE codigo_movimiento=%s AND COALESCE(anulado,'No')<>'Si'""",
        (codmov,),
    )
    filas = cur.rowcount or pendientes
    _insertar_log_detalle(cur, lote_id, item, valor_anterior, "Si", usuario, fecha_db)
    return filas


def _aplicar_insert_contra_anulacion(
    cur,
    dict_cur,
    repo: _RepoLectura,
    item: dict,
    saldos_run: dict[tuple[int, int], Decimal],
    lote_id: str,
    usuario: str,
    fecha_db,
) -> int:
    clave = item.get("clave") or {}
    vn = item.get("valor_nuevo") or {}
    cm_orig = clave.get("codigo_movimiento_original") or vn.get("codigo_movimiento_original")

    dict_cur.execute(
        """SELECT 1 FROM cont_asiento
           WHERE codigo_movimiento_anul=%s
             AND id_concepto_asiento IN (4, 8)
             AND COALESCE(anulado,'No')='No'
             AND COALESCE(codigo_movimiento,0)<>0
           LIMIT 1""",
        (cm_orig,),
    )
    if dict_cur.fetchone():
        return 0

    id_ejercicio = to_int_or_none(vn.get("id_ejercicio"))
    if id_ejercicio is None:
        raise CorreccionContableError(
            f"Item contra-asiento anulación incompleto para cm={cm_orig} (sin id_ejercicio)."
        )

    insertados = 0
    preview_original = vn.get("renglones_original_preview") or []
    if vn.get("regenerar_original") and preview_original:
        if not _asiento_ya_existe(dict_cur, cm_orig):
            nro_asiento_orig = _reservar_nro_asiento_ejercicio(cur, id_ejercicio)
            fecha_orig = to_date_or_none(vn.get("fecha_asiento")) or fecha_db.date()
            desc_asiento_orig = str_or_default(vn.get("desc_asiento"), f"Asiento cm {cm_orig}")
            for r in preview_original:
                id_pc = to_int_or_none(r.get("id_pc"))
                if id_pc is None:
                    continue
                _insertar_renglon_asiento_generico(
                    cur,
                    repo,
                    nro_asiento=nro_asiento_orig,
                    fecha=fecha_orig,
                    id_ejercicio=id_ejercicio,
                    codigo_movimiento=to_int_or_none(cm_orig) or 0,
                    id_pc=id_pc,
                    debe=_r2(r.get("debe_asiento")),
                    haber=_r2(r.get("haber_asiento")),
                    id_concepto=to_int_or_none(r.get("id_concepto_asiento"))
                    or CONCEPTO.get(str_or_default(vn.get("tipo_comprobante")), 3),
                    desc_concepto=str_or_default(r.get("desc_concepto_asiento"), "Compra"),
                    desc_asiento=desc_asiento_orig,
                    desc_renglon=MARCA_REGEN,
                    codigo_movimiento_anul=None,
                    anulado="Si",
                    saldos_run=saldos_run,
                )
                insertados += 1

    preview = vn.get("renglones_preview") or []
    if not preview:
        dict_cur.execute(
            """SELECT id_pc, debe_asiento, haber_asiento, desc_concepto_asiento,
                      desc_asiento, fecha_asiento, id_ejercicio
               FROM cont_asiento WHERE codigo_movimiento=%s""",
            (cm_orig,),
        )
        orig_rows = dict_cur.fetchall()
        if not orig_rows:
            return 0
        id_concepto_anul = to_int_or_none(vn.get("id_concepto_asiento")) or 4
        desc_concepto_anul = str_or_default(vn.get("desc_concepto_asiento"), "Anulación")
        preview = [
            {
                "id_pc": to_int_or_none(r.get("id_pc")),
                "debe_asiento": str(_r2(r.get("haber_asiento"))),
                "haber_asiento": str(_r2(r.get("debe_asiento"))),
                "desc_renglon_asiento": MARCA_ANUL_REGEN,
                "desc_concepto_asiento": desc_concepto_anul,
                "id_concepto_asiento": id_concepto_anul,
            }
            for r in orig_rows
            if _r2(r.get("debe_asiento")) != 0 or _r2(r.get("haber_asiento")) != 0
        ]

    id_concepto_anul = to_int_or_none(vn.get("id_concepto_asiento")) or 4
    desc_concepto_anul = str_or_default(vn.get("desc_concepto_asiento"), "Anulación")
    desc_asiento = str_or_default(vn.get("desc_asiento"), f"Anulación cm {cm_orig}")
    fecha = to_date_or_none(vn.get("fecha_asiento")) or fecha_db.date()

    cm_contra = _reservar_codigo_movimiento(cur)
    nro_asiento = _reservar_nro_asiento_ejercicio(cur, id_ejercicio)
    for r in preview:
        id_pc = to_int_or_none(r.get("id_pc"))
        if id_pc is None:
            continue
        _insertar_renglon_asiento_generico(
            cur,
            repo,
            nro_asiento=nro_asiento,
            fecha=fecha,
            id_ejercicio=id_ejercicio,
            codigo_movimiento=cm_contra,
            id_pc=id_pc,
            debe=_r2(r.get("debe_asiento")),
            haber=_r2(r.get("haber_asiento")),
            id_concepto=to_int_or_none(r.get("id_concepto_asiento")) or id_concepto_anul,
            desc_concepto=str_or_default(r.get("desc_concepto_asiento"), desc_concepto_anul),
            desc_asiento=desc_asiento,
            desc_renglon=str_or_default(r.get("desc_renglon_asiento"), MARCA_ANUL_REGEN),
            codigo_movimiento_anul=to_int_or_none(cm_orig),
            saldos_run=saldos_run,
        )
        insertados += 1

    if insertados == 0:
        return 0

    item_log = {
        **item,
        "clave": {
            **(item.get("clave") or {}),
            "codigo_movimiento": str(cm_contra),
            "codigo_movimiento_anul": str(cm_orig),
        },
    }
    _insertar_log_detalle(cur, lote_id, item_log, None, str(cm_contra), usuario, fecha_db)
    return insertados


def _aplicar_item_anulacion(
    cur,
    dict_cur,
    repo: _RepoLectura,
    item: dict,
    saldos_run: dict[tuple[int, int], Decimal],
    lote_id: str,
    usuario: str,
    fecha_db,
) -> int:
    if item.get("bloqueado"):
        return 0
    accion = item.get("accion")
    if accion == "insert_marcador":
        return _aplicar_insert_marcador_anulacion(cur, dict_cur, item, lote_id, usuario, fecha_db)
    if accion == "marcar_original_anulado":
        return _aplicar_marcar_original_anulado(cur, dict_cur, item, lote_id, usuario, fecha_db)
    if accion == "insert_contra_asiento":
        return _aplicar_insert_contra_anulacion(
            cur, dict_cur, repo, item, saldos_run, lote_id, usuario, fecha_db
        )
    return 0


def _reservar_codigo_movimiento(cur) -> int:
    cur.execute("SELECT CodigoMovimiento FROM codmov WHERE codigo=1 FOR UPDATE")
    row = cur.fetchone()
    cm = to_int_or_none(row[0] if row else None) or 0
    nuevo = cm + 1
    cur.execute("UPDATE codmov SET CodigoMovimiento=%s WHERE codigo=1", (nuevo,))
    return nuevo


def _reservar_nro_asiento_ejercicio(cur, id_ejercicio: int) -> int:
    cur.execute(
        "SELECT nro_asiento_ejercicio FROM cont_ejercicio WHERE id_ejercicio=%s FOR UPDATE",
        (id_ejercicio,),
    )
    row = cur.fetchone()
    if not row:
        raise CorreccionContableError(f"Ejercicio {id_ejercicio} inexistente.")
    nro = to_int_or_none(row[0]) or 0
    cur.execute(
        "UPDATE cont_ejercicio SET nro_asiento_ejercicio=%s WHERE id_ejercicio=%s",
        (nro + 1, id_ejercicio),
    )
    return nro


def _concepto_anulacion(cur, id_concepto_origen: int) -> int:
    cur.execute(
        "SELECT id_concepto_anul FROM cont_concepto_asiento WHERE id_concepto_asiento=%s",
        (id_concepto_origen,),
    )
    row = cur.fetchone()
    concepto = to_int_or_none(row[0] if row else None)
    return concepto if concepto is not None else 4


def _leer_rei_actual_legacy(cur, id_pc: int, id_ejercicio: int, saldo_pc: str | None = None) -> Decimal:
    """REI registrado = suma firmada de renglones concepto 13."""
    if saldo_pc is None:
        cur.execute("SELECT saldo_pc FROM cont_pc WHERE id_pc=%s", (id_pc,))
        row = cur.fetchone()
        if row:
            saldo_pc = str_or_default(row.get("saldo_pc") if isinstance(row, dict) else row[0], "Deudor")
        else:
            saldo_pc = "Deudor"
    return _r2(rei_registrado_cuenta(cur, id_pc, id_ejercicio, saldo_pc))


def _insertar_renglon_asiento_generico(
    cur,
    repo: _RepoLectura,
    *,
    nro_asiento: int,
    fecha,
    id_ejercicio: int,
    codigo_movimiento: int,
    id_pc: int,
    debe: Decimal,
    haber: Decimal,
    id_concepto: int,
    desc_concepto: str,
    desc_asiento: str,
    desc_renglon: str,
    codigo_movimiento_anul: Optional[int] = None,
    anulado: str = "No",
    saldos_run: dict[tuple[int, int], Decimal],
) -> Decimal:
    vdebe, vhaber = _r2(debe), _r2(haber)
    natur = repo.saldo_pc(id_pc) or "Deudor"
    clave_saldo = (id_pc, id_ejercicio)
    if clave_saldo not in saldos_run:
        saldos_run[clave_saldo] = _saldo_inicial_ejercicio(cur, id_pc, id_ejercicio)
    if natur == "Acreedor":
        saldos_run[clave_saldo] += vhaber - vdebe
    else:
        saldos_run[clave_saldo] += vdebe - vhaber
    saldo_asiento = _r2(saldos_run[clave_saldo])
    cur.execute(
        """INSERT INTO cont_asiento
           (nro_asiento, fecha_asiento, id_ejercicio, id_periodo,
            codigo_movimiento, codigo_movimiento_anul, debe_asiento, haber_asiento, saldo_asiento,
            id_pc, desc_renglon_asiento, desc_concepto_asiento,
            id_concepto_asiento, balanceado_asiento, id_usuario,
            desc_asiento, tipo_asiento, anulado)
           VALUES (%s,%s,%s,NULL,%s,%s,%s,%s,%s,%s,%s,%s,%s,'Si',NULL,%s,'Proceso',%s)""",
        (
            nro_asiento,
            fecha,
            id_ejercicio,
            str(codigo_movimiento),
            str(codigo_movimiento_anul) if codigo_movimiento_anul is not None else None,
            str(vdebe),
            str(vhaber),
            str(saldo_asiento),
            id_pc,
            desc_renglon,
            desc_concepto,
            id_concepto,
            desc_asiento,
            anulado,
        ),
    )
    return saldo_asiento


def _anular_asiento_rei(
    cur,
    dict_cur,
    repo: _RepoLectura,
    codmov_original: str,
    id_ejercicio: int,
    lote_id: str,
    usuario: str,
    fecha_db,
    saldos_run: dict[tuple[int, int], Decimal],
) -> int:
    """Marca original ``anulado='Si'`` e inserta contra-asiento reversante."""
    dict_cur.execute(
        """SELECT id_pc, id_concepto_asiento, debe_asiento, haber_asiento,
                  desc_renglon_asiento, desc_concepto_asiento, desc_asiento, fecha_asiento
           FROM cont_asiento
           WHERE codigo_movimiento=%s AND id_ejercicio=%s
             AND COALESCE(anulado,'No')<>'Si'""",
        (codmov_original, id_ejercicio),
    )
    renglones = dict_cur.fetchall()
    if not renglones:
        return 0

    cur.execute(
        """UPDATE cont_asiento SET anulado='Si'
           WHERE codigo_movimiento=%s AND id_ejercicio=%s AND COALESCE(anulado,'No')<>'Si'""",
        (codmov_original, id_ejercicio),
    )
    item_anul = {
        "check_id": CHECK_REI,
        "tabla": "cont_asiento",
        "clave": {"codigo_movimiento": codmov_original, "accion": "anular"},
    }
    _insertar_log_detalle(
        cur,
        lote_id,
        item_anul,
        "activo",
        "anulado",
        usuario,
        fecha_db,
    )

    id_concepto_orig = to_int_or_none(renglones[0].get("id_concepto_asiento")) or CONCEPTO_REI
    id_concepto_anul = _concepto_anulacion(cur, id_concepto_orig)
    cm_contra = _reservar_codigo_movimiento(cur)
    nro_asiento = _reservar_nro_asiento_ejercicio(cur, id_ejercicio)
    fecha = to_date_or_none(renglones[0].get("fecha_asiento")) or fecha_db.date()
    desc_asiento = str_or_default(renglones[0].get("desc_asiento"), "Anulación REI auditoria")

    insertados = 0
    for r in renglones:
        debe = _r2(r.get("debe_asiento"))
        haber = _r2(r.get("haber_asiento"))
        _insertar_renglon_asiento_generico(
            cur,
            repo,
            nro_asiento=nro_asiento,
            fecha=fecha,
            id_ejercicio=id_ejercicio,
            codigo_movimiento=cm_contra,
            id_pc=to_int_or_none(r.get("id_pc")) or 0,
            debe=haber,
            haber=debe,
            id_concepto=id_concepto_anul,
            desc_concepto=str_or_default(r.get("desc_concepto_asiento"), "Anulación"),
            desc_asiento=desc_asiento,
            desc_renglon="Anulación REI auditoria",
            codigo_movimiento_anul=to_int_or_none(codmov_original),
            saldos_run=saldos_run,
        )
        insertados += 1

    item_contra = {
        "check_id": CHECK_REI,
        "tabla": "cont_asiento",
        "clave": {
            "codigo_movimiento": str(cm_contra),
            "codigo_movimiento_anul": codmov_original,
            "accion": "contra_asiento",
        },
    }
    _insertar_log_detalle(
        cur,
        lote_id,
        item_contra,
        codmov_original,
        str(cm_contra),
        usuario,
        fecha_db,
    )
    return insertados


def _generar_asiento_rei_nuevo(
    cur,
    repo: _RepoLectura,
    caso: AprobacionREI,
    lote_id: str,
    usuario: str,
    fecha_db,
    saldos_run: dict[tuple[int, int], Decimal],
) -> int:
    """Genera asiento REI balanceado con importe ``rei_teorico`` (VB6, concepto 13)."""
    importe = _r2(caso.rei_teorico)
    if importe <= 0:
        return 0

    id_pc = caso.id_pc
    id_ejercicio = caso.id_ejercicio
    natur = repo.saldo_pc(id_pc) or "Deudor"
    cuenta_contra = repo.matriz(PARAMATRIZ_REI_CONTRAPARTIDA)
    if cuenta_contra is None:
        raise CorreccionContableError(
            f"No está configurada la contrapartida REI (paramatriz {PARAMATRIZ_REI_CONTRAPARTIDA})."
        )

    debe_cuenta, haber_cuenta = importe, Decimal("0")
    debe_contra, haber_contra = Decimal("0"), importe
    if natur == "Acreedor":
        debe_cuenta, haber_cuenta = Decimal("0"), importe
        debe_contra, haber_contra = importe, Decimal("0")

    cm_nuevo = _reservar_codigo_movimiento(cur)
    nro_asiento = _reservar_nro_asiento_ejercicio(cur, id_ejercicio)
    desc_asiento = DESC_ASIENTO_REI

    _insertar_renglon_asiento_generico(
        cur,
        repo,
        nro_asiento=nro_asiento,
        fecha=fecha_db.date(),
        id_ejercicio=id_ejercicio,
        codigo_movimiento=cm_nuevo,
        id_pc=id_pc,
        debe=debe_cuenta,
        haber=haber_cuenta,
        id_concepto=CONCEPTO_REI,
        desc_concepto="Ajuste inflación",
        desc_asiento=desc_asiento,
        desc_renglon=MARCA_REI_REGEN,
        saldos_run=saldos_run,
    )
    _insertar_renglon_asiento_generico(
        cur,
        repo,
        nro_asiento=nro_asiento,
        fecha=fecha_db.date(),
        id_ejercicio=id_ejercicio,
        codigo_movimiento=cm_nuevo,
        id_pc=cuenta_contra,
        debe=debe_contra,
        haber=haber_contra,
        id_concepto=CONCEPTO_REI,
        desc_concepto="Ajuste inflación",
        desc_asiento=desc_asiento,
        desc_renglon=MARCA_REI_REGEN,
        saldos_run=saldos_run,
    )

    saldo_final = _r2(saldos_run.get((id_pc, id_ejercicio), Decimal("0")))
    cur.execute(
        """UPDATE cont_ejercicio_saldo_cta SET saldo_ejercicio_cta=%s
           WHERE id_pc=%s AND id_ejercicio=%s""",
        (str(saldo_final), id_pc, id_ejercicio),
    )

    item_nuevo = {
        "check_id": CHECK_REI,
        "tabla": "cont_asiento",
        "clave": {"codigo_movimiento": str(cm_nuevo), "id_pc": id_pc, "accion": "nuevo_rei"},
        "valor_nuevo": str(caso.rei_teorico),
        "valor_anterior": str(caso.rei_actual),
    }
    _insertar_log_detalle(
        cur,
        lote_id,
        item_nuevo,
        str(caso.rei_actual),
        str(caso.rei_teorico),
        usuario,
        fecha_db,
    )

    item_saldo = {
        "check_id": CHECK_REI,
        "tabla": "cont_ejercicio_saldo_cta",
        "clave": {"id_pc": id_pc, "id_ejercicio": id_ejercicio},
        "accion": "update",
        "valor_anterior": str(caso.rei_actual),
        "valor_nuevo": str(saldo_final),
    }
    _insertar_log_detalle(
        cur,
        lote_id,
        item_saldo,
        str(caso.rei_actual),
        str(saldo_final),
        usuario,
        fecha_db,
    )
    return 2


def _apply_modo_rei(
    base_empresa: str,
    plan_obj: PlanCorreccion,
    usuario: str,
    *,
    confirmar_reapertura: bool = False,
    autorizador: str = "",
) -> dict[str, Any]:
    """Apply transaccional solo para casos ``AprobacionREI`` aprobados."""
    aprobados = list(
        AprobacionREI.objects.filter(dry_run_id=plan_obj.dry_run_id, estado="aprobado")
    )
    if not aprobados:
        raise CorreccionContableError(
            "No hay casos REI aprobados para aplicar. Revise la pantalla de aprobación REI."
        )

    politica = resolver_politica(base_empresa)
    pool = get_mysql_pool()
    ahora = timezone.now()
    timestamp = ahora.strftime("%Y%m%d_%H%M%S")
    lote_id = f"L{timestamp}-{uuid.uuid4().hex[:8]}"
    plan_json = plan_obj.plan or {}
    propuestas_map = {
        (to_int_or_none(p.get("id_pc")), to_int_or_none(p.get("id_ejercicio"))): p
        for p in (plan_json.get("propuestas_rei") or [])
    }

    with pool.get_connection(base_empresa) as conn:
        repo = _RepoLectura(conn)
        if politica.get("ejercicios_cerrados") == "permitir_con_reapertura":
            cerrados = repo.ejercicios_cerrados()
            if any(c.id_ejercicio in cerrados for c in aprobados) and not confirmar_reapertura:
                raise CorreccionContableError(
                    "El plan REI afecta ejercicios cerrados; confirme la reapertura explícita."
                )
        elif politica.get("ejercicios_cerrados") == "no_tocar":
            cerrados = repo.ejercicios_cerrados()
            bloqueados = [c for c in aprobados if c.id_ejercicio in cerrados]
            if bloqueados:
                raise CorreccionContableError(
                    "Hay casos REI en ejercicios cerrados; no se puede aplicar con la política actual."
                )

        dict_cur = conn.cursor(MySQLdb.cursors.DictCursor)
        for caso in aprobados:
            propuesta = propuestas_map.get((caso.id_pc, caso.id_ejercicio), {})
            if propuesta.get("excluido"):
                raise CorreccionContableError(
                    f"REI no computable para cuenta {caso.id_pc}: "
                    f"{propuesta.get('motivo_exclusion') or 'índices o config insuficientes'}."
                )
            eval_cur = repo.cur()
            evaluacion = evaluar_rei_ejercicio(eval_cur, caso.id_ejercicio)
            cuenta_eval = next(
                (c for c in evaluacion["cuentas"] if c.id_pc == caso.id_pc),
                None,
            )
            if cuenta_eval is None or not cuenta_eval.computable:
                motivo = (
                    cuenta_eval.motivo_no_computable
                    if cuenta_eval
                    else evaluacion.get("motivo_ind_cierre")
                )
                raise CorreccionContableError(
                    f"REI no computable para cuenta {caso.id_pc}: {motivo or 'sin índices'}."
                )
            actual = _leer_rei_actual_legacy(dict_cur, caso.id_pc, caso.id_ejercicio, cuenta_eval.saldo_pc)
            if _r2(actual) != _r2(caso.rei_actual):
                raise CorreccionContableError(
                    f"Concurrencia REI cuenta {caso.id_pc}: REI registrado actual {actual} "
                    f"difiere del dry-run ({caso.rei_actual}). Ejecute un nuevo dry-run."
                )

    reapertura_flag = 1 if (
        politica.get("ejercicios_cerrados") == "permitir_con_reapertura"
        and confirmar_reapertura
    ) else 0

    filas_aplicadas = 0
    with pool.get_connection(base_empresa) as conn:
      try:
        conn.autocommit(False)
        cur = conn.cursor()
        dict_cur = conn.cursor(MySQLdb.cursors.DictCursor)
        repo = _RepoLectura(conn)
        fecha_db = timezone.localtime(ahora).replace(tzinfo=None)

        cur.execute(
            """INSERT INTO cont_audit_correccion_lote
               (lote_id, base_empresa, dry_run_id, config_hash, usuario, fecha,
                estado, reapertura_flag, autorizador, backups_json)
               VALUES (%s,%s,%s,%s,%s,%s,'aplicado',%s,%s,%s)""",
            (
                lote_id,
                base_empresa,
                str(plan_obj.dry_run_id),
                plan_obj.config_hash,
                usuario,
                fecha_db,
                reapertura_flag,
                autorizador or None,
                "{}",
            ),
        )

        saldos_run: dict[tuple[int, int], Decimal] = {}
        for caso in aprobados:
            propuesta = propuestas_map.get((caso.id_pc, caso.id_ejercicio), {})
            if propuesta.get("excluido"):
                conn.rollback()
                raise CorreccionContableError(
                    f"REI no computable para cuenta {caso.id_pc}: "
                    f"{propuesta.get('motivo_exclusion') or 'índices o config insuficientes'}."
                )

            eval_cur = repo.cur()
            evaluacion = evaluar_rei_ejercicio(eval_cur, caso.id_ejercicio)
            cuenta_eval = next(
                (c for c in evaluacion["cuentas"] if c.id_pc == caso.id_pc),
                None,
            )
            if cuenta_eval is None or not cuenta_eval.computable:
                conn.rollback()
                motivo = (
                    cuenta_eval.motivo_no_computable
                    if cuenta_eval
                    else evaluacion.get("motivo_ind_cierre")
                )
                raise CorreccionContableError(
                    f"REI no computable para cuenta {caso.id_pc}: {motivo or 'sin índices'}."
                )

            actual = _leer_rei_actual_legacy(
                dict_cur, caso.id_pc, caso.id_ejercicio, cuenta_eval.saldo_pc
            )
            if _r2(actual) != _r2(caso.rei_actual):
                conn.rollback()
                raise CorreccionContableError(
                    f"Concurrencia REI cuenta {caso.id_pc}: REI registrado actual {actual} "
                    f"difiere del dry-run ({caso.rei_actual}). Ejecute un nuevo dry-run."
                )

            codigos = propuesta.get("codigos_movimiento_rei") or _listar_codigos_rei_cuenta(
                dict_cur, caso.id_pc, caso.id_ejercicio
            )
            for codmov in codigos:
                filas_aplicadas += _anular_asiento_rei(
                    cur,
                    dict_cur,
                    repo,
                    str_or_default(codmov),
                    caso.id_ejercicio,
                    lote_id,
                    usuario,
                    fecha_db,
                    saldos_run,
                )
            filas_aplicadas += _generar_asiento_rei_nuevo(
                cur, repo, caso, lote_id, usuario, fecha_db, saldos_run
            )

        conn.commit()
        for caso in aprobados:
            caso.estado = "aplicado"
            caso.save(update_fields=["estado"])
      except CorreccionContableError:
        try:
            conn.rollback()
        except Exception:
            pass
        raise
      except Exception as exc:
        try:
            conn.rollback()
        except Exception:
            pass
        logger.exception("apply rei: error transaccional base=%s lote=%s", base_empresa, lote_id)
        raise CorreccionContableError(f"Error al aplicar corrección REI: {exc}") from exc
      finally:
        try:
            conn.autocommit(True)
        except Exception:
            pass

    plan_obj.estado = "aplicado"
    plan_obj.save(update_fields=["estado"])

    return {
        "ok": True,
        "lote_id": lote_id,
        "mensaje": f"Corrección REI aplicada ({len(aprobados)} caso(s) aprobado(s)).",
        "filas_aplicadas": filas_aplicadas,
        "casos_rei": len(aprobados),
        "backups": {},
        "fecha": _fecha_ui(ahora),
        "reapertura_flag": bool(reapertura_flag),
        "modo": "rei",
    }


def _requiere_reapertura(items: list[dict], repo: _RepoLectura) -> bool:
    cerrados = repo.ejercicios_cerrados()
    for item in items:
        clave = item.get("clave") or {}
        id_ej = to_int_or_none(clave.get("id_ejercicio"))
        if id_ej is None:
            vn = item.get("valor_nuevo") or {}
            if isinstance(vn, dict):
                id_ej = to_int_or_none(vn.get("id_ejercicio"))
        if id_ej in cerrados:
            return True
    return False


def _evento_progreso_apply(
    *,
    phase: str,
    current: int,
    total: int,
    label: str = "",
) -> dict:
    return {
        "type": "progress",
        "phase": phase,
        "current": current,
        "total": total,
        "label": label,
    }


def _label_progreso_apply_item(item: dict, idx: int, total: int) -> str:
    check_id = str_or_default(item.get("check_id"))
    tabla = str_or_default(item.get("tabla"))
    if check_id:
        return f"{check_id} ({idx}/{total})"
    if tabla:
        return f"{tabla} ({idx}/{total})"
    return f"Aplicando ítem {idx}/{total}"


def _yield_progreso_write(
    progress_idx: list[int],
    total: int,
    item: dict,
    intervalo: int,
) -> dict | None:
    progress_idx[0] += 1
    idx = progress_idx[0]
    if idx == 1 or idx == total or idx % intervalo == 0:
        return _evento_progreso_apply(
            phase="write",
            current=idx,
            total=total,
            label=_label_progreso_apply_item(item, idx, total),
        )
    return None


def _apply_iter(
    base_empresa: str,
    dry_run_id: str,
    usuario: str,
    *,
    tiene_permiso_corregir: bool = False,
    confirmar_reapertura: bool = False,
    autorizador: str = "",
) -> Iterator[dict]:
    """Generador interno: eventos progress y result al aplicar corrección (modo general)."""
    if not tiene_permiso_corregir:
        raise CorreccionContableError(
            "No tiene permiso para aplicar correcciones contables (contabilidad.auditoria.corregir)."
        )

    try:
        plan_obj = PlanCorreccion.objects.get(dry_run_id=dry_run_id)
    except PlanCorreccion.DoesNotExist as exc:
        raise CorreccionContableError("No existe un plan dry-run con ese identificador.") from exc

    if plan_obj.base_empresa != base_empresa:
        raise CorreccionContableError("El plan no corresponde a la empresa indicada.")

    if plan_obj.estado != "propuesto":
        raise CorreccionContableError(
            f"El plan está en estado «{plan_obj.estado}»; no se puede aplicar."
        )

    ahora = timezone.now()
    if plan_obj.expira_en and ahora >= plan_obj.expira_en:
        plan_obj.estado = "expirado"
        plan_obj.save(update_fields=["estado"])
        raise CorreccionContableError(
            "El plan expiró; ejecute un nuevo dry-run antes de aplicar."
        )

    politica = resolver_politica(base_empresa)
    config_actual = calcular_config_hash(politica)
    if plan_obj.config_hash != config_actual:
        plan_obj.estado = "invalidado"
        plan_obj.save(update_fields=["estado"])
        raise CorreccionContableError(
            "La política cambió desde el dry-run; ejecute un nuevo dry-run."
        )

    plan_json = plan_obj.plan or {}
    items_raw = plan_json.get("items") or []
    items = _filtrar_items_aplicables(items_raw)

    pool = get_mysql_pool()
    with pool.get_connection(base_empresa) as conn:
        repo = _RepoLectura(conn)
        if politica.get("ejercicios_cerrados") == "permitir_con_reapertura":
            if _requiere_reapertura(items, repo) and not confirmar_reapertura:
                raise CorreccionContableError(
                    "El plan afecta ejercicios cerrados; confirme la reapertura explícita."
                )
        elif politica.get("ejercicios_cerrados") == "no_tocar":
            _marcar_exclusiones(items, politica, repo)
            items = _filtrar_items_aplicables(items)

        fp_actual = _calcular_fingerprint_desde_legacy(conn, items)
        if fp_actual != plan_obj.data_fingerprint:
            plan_obj.estado = "invalidado"
            plan_obj.save(update_fields=["estado"])
            raise CorreccionContableError(
                "Concurrencia detectada: los datos cambiaron desde el dry-run. "
                "Ejecute un nuevo dry-run."
            )

    if not items:
        plan_obj.estado = "aplicado"
        plan_obj.save(update_fields=["estado"])
        yield {
            "type": "result",
            "payload": {
                "ok": True,
                "lote_id": None,
                "mensaje": "Plan vacío; no hubo cambios que aplicar.",
                "filas_aplicadas": 0,
            },
        }
        return

    total_items = len(items)
    timestamp = ahora.strftime("%Y%m%d_%H%M%S")
    lote_id = f"L{timestamp}-{uuid.uuid4().hex[:8]}"
    reapertura_flag = 1 if (
        politica.get("ejercicios_cerrados") == "permitir_con_reapertura"
        and confirmar_reapertura
    ) else 0

    filas_aplicadas = 0
    with pool.get_connection(base_empresa) as conn:
        try:
            conn.autocommit(False)
            cur = conn.cursor()
            dict_cur = conn.cursor(MySQLdb.cursors.DictCursor)
            repo = _RepoLectura(conn)
            fecha_db = timezone.localtime(ahora).replace(tzinfo=None)

            cur.execute(
                """INSERT INTO cont_audit_correccion_lote
                   (lote_id, base_empresa, dry_run_id, config_hash, usuario, fecha,
                    estado, reapertura_flag, autorizador, backups_json)
                   VALUES (%s,%s,%s,%s,%s,%s,'aplicado',%s,%s,%s)""",
                (
                    lote_id,
                    base_empresa,
                    str(plan_obj.dry_run_id),
                    plan_obj.config_hash,
                    usuario,
                    fecha_db,
                    reapertura_flag,
                    autorizador or None,
                    "{}",
                ),
            )

            _bloquear_filas_objetivo(dict_cur, items)

            fp_tx = _calcular_fingerprint_desde_legacy(conn, items)
            if fp_tx != plan_obj.data_fingerprint:
                conn.rollback()
                plan_obj.estado = "invalidado"
                plan_obj.save(update_fields=["estado"])
                raise CorreccionContableError(
                    "Concurrencia detectada durante la transacción. Ejecute un nuevo dry-run."
                )

            items_ordenados = _orden_apply_items(items)
            total = len(items_ordenados)
            intervalo = 5 if total > 100 else 1
            progress_idx = [0]
            saldos_run: dict[tuple[int, int], Decimal] = {}
            cuentas_libro_mayor: set[tuple[int, int]] = set()

            # Pre-regeneración de asientos (REC-18, antes del orden REC-07 2→3→4).
            asientos_por_cm: dict[str, list[dict]] = defaultdict(list)
            for item in items_ordenados:
                if (
                    item.get("tabla") == "cont_asiento"
                    and item.get("accion") == "insert"
                    and item.get("check_id") in CHECKS_REGENERACION_ASIENTO
                ):
                    cm = str_or_default((item.get("valor_nuevo") or {}).get("codigo_movimiento"))
                    asientos_por_cm[cm].append(item)

            for renglones in asientos_por_cm.values():
                filas_aplicadas += _aplicar_asiento_completo(
                    cur, repo, renglones, saldos_run, lote_id, usuario, fecha_db
                )
                for item in renglones:
                    evt = _yield_progreso_write(progress_idx, total, item, intervalo)
                    if evt is not None:
                        yield evt

            # REC-19: reparación anulaciones incompletas (antes de concepto REC-07 paso 2).
            for item in items_ordenados:
                if item.get("check_id") != CHECK_ANULACION:
                    continue
                filas_aplicadas += _aplicar_item_anulacion(
                    cur, dict_cur, repo, item, saldos_run, lote_id, usuario, fecha_db
                )
                evt = _yield_progreso_write(progress_idx, total, item, intervalo)
                if evt is not None:
                    yield evt

            # REC-07 paso 2: concepto_anulacion_incoherente (UPDATE cont_asiento).
            for item in items_ordenados:
                if item.get("check_id") != CHECK_CONCEPTO_ANUL:
                    continue
                _aplicar_item_concepto(cur, item, lote_id, usuario, fecha_db)
                filas_aplicadas += 1
                evt = _yield_progreso_write(progress_idx, total, item, intervalo)
                if evt is not None:
                    yield evt

            # REC-07 pasos 3 y 4: filas saldo faltantes (INSERT) → recompute (UPDATE).
            for item in items_ordenados:
                tabla = item.get("tabla")
                if tabla not in ("cont_ejercicio_saldo_cta", "cont_periodo_saldo_cta"):
                    continue
                id_pc = to_int_or_none((item.get("clave") or {}).get("id_pc"))
                if id_pc is not None and repo.saldo_pc(id_pc) is None:
                    continue
                if item.get("accion") == "insert" and _fila_saldo_existe(cur, item):
                    continue
                _aplicar_item_saldo(cur, item, lote_id, usuario, fecha_db)
                filas_aplicadas += 1
                if tabla == "cont_ejercicio_saldo_cta":
                    id_ejercicio = to_int_or_none((item.get("clave") or {}).get("id_ejercicio"))
                    if id_pc is not None and id_ejercicio is not None:
                        cuentas_libro_mayor.add((id_pc, id_ejercicio))
                evt = _yield_progreso_write(progress_idx, total, item, intervalo)
                if evt is not None:
                    yield evt

            for id_pc, id_ejercicio in sorted(cuentas_libro_mayor):
                recalcular_saldo_asiento_cuenta(
                    cur,
                    dict_cur,
                    id_pc,
                    id_ejercicio,
                )

            yield _evento_progreso_apply(
                phase="finalize",
                current=total,
                total=total,
                label="Finalizando…",
            )

            conn.commit()
        except CorreccionContableError:
            try:
                conn.rollback()
            except Exception:
                pass
            raise
        except Exception as exc:
            try:
                conn.rollback()
            except Exception:
                pass
            logger.exception("apply: error transaccional base=%s lote=%s", base_empresa, lote_id)
            raise CorreccionContableError(f"Error al aplicar corrección: {exc}") from exc
        finally:
            try:
                conn.autocommit(True)
            except Exception:
                pass

    plan_obj.estado = "aplicado"
    plan_obj.save(update_fields=["estado"])

    yield {
        "type": "result",
        "payload": {
            "ok": True,
            "lote_id": lote_id,
            "mensaje": "Corrección aplicada correctamente.",
            "filas_aplicadas": filas_aplicadas,
            "backups": {},
            "fecha": _fecha_ui(ahora),
            "reapertura_flag": bool(reapertura_flag),
        },
    }


def apply(
    base_empresa: str,
    dry_run_id: str,
    usuario: str,
    *,
    tiene_permiso_corregir: bool = False,
    confirmar_reapertura: bool = False,
    autorizador: str = "",
    modo: str = "general",
    on_progress: Callable[[dict], None] | None = None,
) -> dict[str, Any]:
    """
    Aplica un plan dry-run en MySQL legacy (Fase 3).

    Requiere permiso ``contabilidad.auditoria.corregir``. El flag
    ``tiene_permiso_corregir`` debe venir validado desde la vista.
    Disponible en cualquier entorno (development incluido) para pruebas;
    la salvaguarda operativa es el permiso + confirmación explícita en UI.

    ``modo='rei'`` procesa únicamente casos ``AprobacionREI`` con estado aprobado.
    """
    if not tiene_permiso_corregir:
        raise CorreccionContableError(
            "No tiene permiso para aplicar correcciones contables (contabilidad.auditoria.corregir)."
        )

    try:
        plan_obj = PlanCorreccion.objects.get(dry_run_id=dry_run_id)
    except PlanCorreccion.DoesNotExist as exc:
        raise CorreccionContableError("No existe un plan dry-run con ese identificador.") from exc

    if plan_obj.base_empresa != base_empresa:
        raise CorreccionContableError("El plan no corresponde a la empresa indicada.")

    if plan_obj.estado != "propuesto":
        raise CorreccionContableError(
            f"El plan está en estado «{plan_obj.estado}»; no se puede aplicar."
        )

    ahora = timezone.now()
    if plan_obj.expira_en and ahora >= plan_obj.expira_en:
        plan_obj.estado = "expirado"
        plan_obj.save(update_fields=["estado"])
        raise CorreccionContableError(
            "El plan expiró; ejecute un nuevo dry-run antes de aplicar."
        )

    politica = resolver_politica(base_empresa)
    config_actual = calcular_config_hash(politica)
    if plan_obj.config_hash != config_actual:
        plan_obj.estado = "invalidado"
        plan_obj.save(update_fields=["estado"])
        raise CorreccionContableError(
            "La política cambió desde el dry-run; ejecute un nuevo dry-run."
        )

    if modo == "rei":
        return _apply_modo_rei(
            base_empresa,
            plan_obj,
            usuario,
            confirmar_reapertura=confirmar_reapertura,
            autorizador=autorizador,
        )

    resultado: dict | None = None
    for evento in _apply_iter(
        base_empresa,
        dry_run_id,
        usuario,
        tiene_permiso_corregir=tiene_permiso_corregir,
        confirmar_reapertura=confirmar_reapertura,
        autorizador=autorizador,
    ):
        if evento.get("type") == "progress" and on_progress is not None:
            on_progress(evento)
        elif evento.get("type") == "result":
            resultado = evento["payload"]
    if resultado is None:
        raise CorreccionContableError("No se obtuvo resultado del apply.")
    return resultado


def rollback_lote(
    base_empresa: str,
    lote_id: str,
    usuario: str,
    *,
    tiene_permiso_corregir: bool = False,
) -> dict[str, Any]:
    """Reversión de lotes deshabilitada: las correcciones ya no generan backup de tablas."""
    if not tiene_permiso_corregir:
        raise CorreccionContableError(
            "No tiene permiso para revertir correcciones contables."
        )

    raise CorreccionContableError(
        "La reversión de lotes ya no está disponible: las correcciones no generan backup de tablas."
    )
