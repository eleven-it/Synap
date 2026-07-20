"""Checks de integración compras/pagos ↔ contabilidad."""
from __future__ import annotations

from decimal import Decimal

from core.utils.administranet_types import to_decimal_or_none, to_int_or_none, str_or_default

from contabilidad_audit.services.checks._sql import (
    clasificar_delta,
    filtro_anulados_sql,
    id_ejercicio_filtro,
)
from contabilidad_audit.services.resultados import (
    CorridaContexto,
    Diferencia,
    audit_result_error,
    construir_audit_result,
)

TIPOS_COMPRA_PAGO = ("FA", "FC", "OP")


def comprobante_compra_pago_sin_asiento(base_empresa, filtros, politica, contexto: CorridaContexto):
    """Portado de cont_reconstruccion_compras_pagos.py dryrun-missing (solo lectura)."""
    check_id = "comprobante_compra_pago_sin_asiento"
    titulo = "Comprobante compra/pago sin asiento contable"
    severidad = "critico"
    try:
        cur = contexto.cursor
        cur.execute(
            """
            SELECT cp.CodigoMovimiento, cp.TipoComprobante, cp.NroComprobante,
                   cp.CodSucursal, cp.ImporteCompra, cp.Fecha
            FROM cuentaproveedor cp
            JOIN sucursales s ON s.id_sucursal = cp.CodSucursal
            WHERE s.cont = 'Si'
              AND COALESCE(cp.Anulado, 'No') <> 'Si'
              AND cp.TipoComprobante IN ('FA', 'FC', 'OP')
              AND COALESCE(cp.CodigoMovimiento, 0) <> 0
              AND NOT EXISTS (
                  SELECT 1 FROM cont_asiento ca
                  WHERE ca.codigo_movimiento = cp.CodigoMovimiento
                    AND COALESCE(ca.codigo_movimiento, 0) <> 0
              )
            """
        )
        rows = cur.fetchall()
        diferencias = [
            Diferencia(
                codigo_movimiento=str_or_default(r[0]),
                referencia_hallazgo="H51" if str_or_default(r[1]) in ("FA", "FC") else "H52",
                detalle={
                    "TipoComprobante": str_or_default(r[1]),
                    "NroComprobante": str_or_default(r[2]),
                    "CodSucursal": to_int_or_none(r[3]),
                    "ImporteCompra": str(to_decimal_or_none(r[4]) or ""),
                    "Fecha": str_or_default(r[5]),
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
            resumen={"tipos": list(TIPOS_COMPRA_PAGO)},
            contexto=contexto,
        )
    except Exception as exc:
        return audit_result_error(
            check_id=check_id, titulo=titulo, severidad=severidad, contexto=contexto, mensaje=str(exc)
        )


comprobante_compra_pago_sin_asiento.check_id = "comprobante_compra_pago_sin_asiento"
comprobante_compra_pago_sin_asiento.titulo = "Comprobante compra/pago sin asiento contable"
comprobante_compra_pago_sin_asiento.severidad = "critico"


def asiento_compra_pago_desbalanceado_saldo_null(base_empresa, filtros, politica, contexto: CorridaContexto):
    check_id = "asiento_compra_pago_desbalanceado_saldo_null"
    titulo = "Asiento compra/pago desbalanceado o saldo NULL"
    severidad = "alto"
    try:
        id_ejercicio = id_ejercicio_filtro(filtros)
        cur = contexto.cursor
        filtro_anul = filtro_anulados_sql(politica, "a")
        cur.execute(
            f"""
            SELECT cp.CodigoMovimiento,
                   SUM(COALESCE(a.debe_asiento, 0)) AS sum_debe,
                   SUM(COALESCE(a.haber_asiento, 0)) AS sum_haber,
                   SUM(CASE WHEN a.saldo_asiento IS NULL THEN 1 ELSE 0 END) AS renglones_saldo_null
            FROM cuentaproveedor cp
            JOIN sucursales s ON s.id_sucursal = cp.CodSucursal
            JOIN cont_asiento a ON a.codigo_movimiento = cp.CodigoMovimiento
            WHERE s.cont = 'Si'
              AND COALESCE(cp.Anulado, 'No') <> 'Si'
              AND cp.TipoComprobante IN ('FA', 'FC', 'OP')
              AND COALESCE(cp.CodigoMovimiento, 0) <> 0
              AND COALESCE(a.codigo_movimiento, 0) <> 0
              AND a.id_ejercicio = %s
              {filtro_anul}
            GROUP BY cp.CodigoMovimiento
            """,
            (id_ejercicio,),
        )
        rows = cur.fetchall()
        diferencias: list[Diferencia] = []
        for row in rows:
            codmov = str_or_default(row[0])
            sum_debe = to_decimal_or_none(row[1]) or Decimal("0")
            sum_haber = to_decimal_or_none(row[2]) or Decimal("0")
            reng_null = to_int_or_none(row[3]) or 0
            delta = sum_debe - sum_haber
            reportar_balance, _ = clasificar_delta(delta, politica)
            if reportar_balance:
                diferencias.append(
                    Diferencia(
                        codigo_movimiento=codmov,
                        id_ejercicio=id_ejercicio,
                        valor_esperado=sum_haber,
                        valor_actual=sum_debe,
                        delta=delta,
                        referencia_hallazgo="H53",
                        detalle={"sum_debe": str(sum_debe), "sum_haber": str(sum_haber), "motivo": "desbalance"},
                    )
                )
            elif reng_null > 0:
                diferencias.append(
                    Diferencia(
                        codigo_movimiento=codmov,
                        id_ejercicio=id_ejercicio,
                        referencia_hallazgo="H53",
                        detalle={"renglones_saldo_null": reng_null},
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


asiento_compra_pago_desbalanceado_saldo_null.check_id = "asiento_compra_pago_desbalanceado_saldo_null"
asiento_compra_pago_desbalanceado_saldo_null.titulo = "Asiento compra/pago desbalanceado o saldo NULL"
asiento_compra_pago_desbalanceado_saldo_null.severidad = "alto"


def integridad_anulacion_compra_pago(base_empresa, filtros, politica, contexto: CorridaContexto):
    check_id = "integridad_anulacion_compra_pago"
    titulo = "Integridad de anulación compra/pago"
    severidad = "alto"
    try:
        cur = contexto.cursor
        cur.execute(
            """
            SELECT cp.CodigoMovimiento, cp.TipoComprobante, cp.NroComprobante
            FROM cuentaproveedor cp
            JOIN sucursales s ON s.id_sucursal = cp.CodSucursal
            WHERE s.cont = 'Si'
              AND COALESCE(cp.Anulado, 'No') = 'Si'
              AND cp.TipoComprobante IN ('FA', 'FC', 'OP')
              AND COALESCE(cp.CodigoMovimiento, 0) <> 0
            """
        )
        originales = cur.fetchall()
        diferencias: list[Diferencia] = []
        for row in originales:
            cm = row[0]
            cm_str = str_or_default(cm)
            cur.execute(
                """
                SELECT COUNT(*) FROM cuentaproveedor
                WHERE CodigoMovimiento = 0
                  AND codigo_movimiento_anul = %s
                """,
                (cm,),
            )
            tiene_marcador = (cur.fetchone()[0] or 0) > 0
            cur.execute(
                """
                SELECT COUNT(*) FROM cont_asiento
                WHERE codigo_movimiento = %s AND COALESCE(anulado, 'No') = 'Si'
                """,
                (cm,),
            )
            original_anulado = (cur.fetchone()[0] or 0) > 0
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
            problemas = []
            if not tiene_marcador:
                problemas.append("falta_marcador_cuentaproveedor_cm0")
            if not original_anulado:
                problemas.append("asiento_original_no_anulado")
            if contra_tot is None:
                problemas.append("falta_contra_asiento")
            elif orig_tot is not None:
                od = to_decimal_or_none(orig_tot[1]) or Decimal("0")
                oh = to_decimal_or_none(orig_tot[2]) or Decimal("0")
                cd = to_decimal_or_none(contra_tot[1]) or Decimal("0")
                ch = to_decimal_or_none(contra_tot[2]) or Decimal("0")
                if abs(od - ch) > Decimal("0.005") or abs(oh - cd) > Decimal("0.005"):
                    problemas.append("contra_no_invierte_original")
            if problemas:
                diferencias.append(
                    Diferencia(
                        codigo_movimiento=cm_str,
                        referencia_hallazgo="H53",
                        detalle={
                            "TipoComprobante": str_or_default(row[1]),
                            "NroComprobante": str_or_default(row[2]),
                            "problemas": problemas,
                        },
                    )
                )
        return construir_audit_result(
            check_id=check_id,
            titulo=titulo,
            severidad=severidad,
            ok=len(diferencias) == 0,
            total_evaluado=len(originales),
            diferencias=diferencias,
            resumen={},
            contexto=contexto,
        )
    except Exception as exc:
        return audit_result_error(
            check_id=check_id, titulo=titulo, severidad=severidad, contexto=contexto, mensaje=str(exc)
        )


integridad_anulacion_compra_pago.check_id = "integridad_anulacion_compra_pago"
integridad_anulacion_compra_pago.titulo = "Integridad de anulación compra/pago"
integridad_anulacion_compra_pago.severidad = "alto"
