"""Checks de integración ventas/cobranzas ↔ contabilidad (`cuentacliente`)."""
from __future__ import annotations

from core.utils.administranet_types import to_decimal_or_none, to_int_or_none, str_or_default

from contabilidad_audit.services.resultados import (
    CorridaContexto,
    Diferencia,
    audit_result_error,
    construir_audit_result,
)

# Facturas de venta en cuentacliente + recibos de cobranza.
# FA/FB/FC/FE/FM aquí son venta (no confundir con FA/FC de cuentaproveedor = compra).
TIPOS_VENTA = ("FA", "FB", "FC", "FE", "FM")
TIPOS_COBRANZA = ("REC",)
TIPOS_VENTA_COBRANZA = TIPOS_VENTA + TIPOS_COBRANZA


def comprobante_venta_cobranza_sin_asiento(base_empresa, filtros, politica, contexto: CorridaContexto):
    """
    Detecta FA/FB/FC/FE/FM/REC en ``cuentacliente`` con CodigoMovimiento>0
    sin filas en ``cont_asiento`` (espejo de ``comprobante_compra_pago_sin_asiento``).

    Gating: solo punto de venta con ``cont='Si'`` (regla AdministraNET para clientes).
    Excluye anulados y marcadores ``CodigoMovimiento=0``.
    """
    del base_empresa, filtros, politica  # firma uniforme del registry
    check_id = "comprobante_venta_cobranza_sin_asiento"
    titulo = "Comprobante venta/cobranza sin asiento contable"
    severidad = "critico"
    try:
        cur = contexto.cursor
        tipos_sql = ", ".join(f"'{t}'" for t in TIPOS_VENTA_COBRANZA)
        cur.execute(
            f"""
            SELECT cc.CodigoMovimiento, cc.TipoComprobante, cc.NroComprobante,
                   cc.CodSucursal, cc.id_pv,
                   COALESCE(cc.ImporteVenta, 0) AS ImporteVenta,
                   COALESCE(cc.ImporteCobro, cc.TotalRecibo, 0) AS ImporteCobro,
                   cc.Fecha
            FROM cuentacliente cc
            JOIN punto_venta pv ON pv.id_punto_venta = cc.id_pv
            WHERE COALESCE(cc.Anulado, 'No') <> 'Si'
              AND cc.TipoComprobante IN ({tipos_sql})
              AND COALESCE(cc.CodigoMovimiento, 0) <> 0
              AND COALESCE(pv.cont, 'No') = 'Si'
              AND NOT EXISTS (
                  SELECT 1 FROM cont_asiento ca
                  WHERE ca.codigo_movimiento = cc.CodigoMovimiento
                    AND COALESCE(ca.codigo_movimiento, 0) <> 0
              )
            """
        )
        rows = cur.fetchall()
        diferencias = []
        for r in rows:
            tipo = str_or_default(r[1] if not isinstance(r, dict) else r.get("TipoComprobante"))
            if isinstance(r, dict):
                cm = r.get("CodigoMovimiento")
                nro = r.get("NroComprobante")
                suc = r.get("CodSucursal")
                id_pv = r.get("id_pv")
                imp_v = r.get("ImporteVenta")
                imp_c = r.get("ImporteCobro")
                fecha = r.get("Fecha")
            else:
                cm, _tipo, nro, suc, id_pv, imp_v, imp_c, fecha = (
                    r[0], r[1], r[2], r[3], r[4], r[5], r[6], r[7]
                )
            ref = "H55" if tipo == "REC" else "H54"
            importe = imp_c if tipo == "REC" else imp_v
            diferencias.append(
                Diferencia(
                    codigo_movimiento=str_or_default(cm),
                    referencia_hallazgo=ref,
                    detalle={
                        "TipoComprobante": tipo,
                        "NroComprobante": str_or_default(nro),
                        "CodSucursal": to_int_or_none(suc),
                        "id_pv": to_int_or_none(id_pv),
                        "Importe": str(to_decimal_or_none(importe) or ""),
                        "ImporteVenta": str(to_decimal_or_none(imp_v) or ""),
                        "ImporteCobro": str(to_decimal_or_none(imp_c) or ""),
                        "Fecha": str_or_default(fecha),
                    },
                )
            )
        por_tipo: dict[str, int] = {}
        for d in diferencias:
            t = (d.detalle or {}).get("TipoComprobante") or "?"
            por_tipo[t] = por_tipo.get(t, 0) + 1
        return construir_audit_result(
            check_id=check_id,
            titulo=titulo,
            severidad=severidad,
            ok=len(diferencias) == 0,
            total_evaluado=len(rows),
            diferencias=diferencias,
            resumen={
                "tipos": list(TIPOS_VENTA_COBRANZA),
                "por_tipo": por_tipo,
                "conceptos": {"venta": 1, "cobranza": 5},
            },
            contexto=contexto,
        )
    except Exception as exc:
        return audit_result_error(
            check_id=check_id, titulo=titulo, severidad=severidad, contexto=contexto, mensaje=str(exc)
        )


comprobante_venta_cobranza_sin_asiento.check_id = "comprobante_venta_cobranza_sin_asiento"
comprobante_venta_cobranza_sin_asiento.titulo = "Comprobante venta/cobranza sin asiento contable"
comprobante_venta_cobranza_sin_asiento.severidad = "critico"
