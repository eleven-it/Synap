#!/usr/bin/env python
"""Registro de los asientos regenerados por la auditoría (bug factura/OP sin asiento).

SOLO LECTURA. Lista los asientos insertados por `apply_missing`
(`cont_reconstruccion_compras_pagos.py`), identificados por la marca de
trazabilidad en `desc_renglon_asiento`, enlazados con `cuentaproveedor`
por `codigo_movimiento`, para validación manual.

Uso:
    docker exec Synap_app python legacy_db/scripts/cont_registro_asientos_regenerados.py

Salidas (en docs/general/):
    - REGISTRO_ASIENTOS_REGENERADOS_resumen.csv   (1 fila por asiento)
    - REGISTRO_ASIENTOS_REGENERADOS_detalle.csv    (1 fila por renglón)
"""
import csv
import os
from decimal import Decimal

import MySQLdb
import MySQLdb.cursors

DB = dict(
    host=os.environ.get("DB_HOST", "190.15.214.142"),
    port=int(os.environ.get("DB_PORT", "3306")),
    user=os.environ.get("DB_USER", "administranet"),
    passwd=os.environ.get("DB_PASSWORD", "a7v8xx0805"),
    db=os.environ.get("DB_NAME", "administranet89"),
    charset="latin1",
)

MARCA_REGEN = "REGEN auditoria (bug factura/OP sin asiento)"
SALIDA_DIR = os.environ.get("SALIDA_DIR", "docs/general")


def d(v):
    return Decimal(str(v)) if v is not None else Decimal("0")


def fecha_es(v):
    """Convierte date/datetime/str a dd/MM/yyyy (regla Synap)."""
    if v is None:
        return ""
    try:
        return v.strftime("%d/%m/%Y")
    except AttributeError:
        s = str(v)
        # yyyy-MM-dd -> dd/MM/yyyy
        if len(s) >= 10 and s[4] == "-" and s[7] == "-":
            return f"{s[8:10]}/{s[5:7]}/{s[0:4]}"
        return s


def main():
    conn = MySQLdb.connect(**DB)
    cur = conn.cursor(MySQLdb.cursors.DictCursor)

    # Detalle: cada renglón regenerado + datos del comprobante y de la cuenta.
    cur.execute(
        """
        SELECT a.codigo_movimiento, a.nro_asiento, a.id_ejercicio, a.id_periodo,
               a.fecha_asiento, a.id_pc, a.debe_asiento, a.haber_asiento,
               a.saldo_asiento, a.id_concepto_asiento, a.desc_concepto_asiento,
               a.desc_asiento, a.anulado,
               pc.cod_pc, pc.descrip_pc, pc.saldo_pc,
               cp.tipo, cp.nro_comprobante, cp.fecha_cp, cp.importe
        FROM cont_asiento a
        LEFT JOIN cont_pc pc ON pc.id_pc = a.id_pc
        LEFT JOIN (
            SELECT CodigoMovimiento,
                   MIN(TipoComprobante) AS tipo,
                   MIN(NroComprobante)  AS nro_comprobante,
                   MIN(Fecha)           AS fecha_cp,
                   SUM(COALESCE(ImporteCompra,0)) AS importe
            FROM cuentaproveedor
            GROUP BY CodigoMovimiento
        ) cp ON cp.CodigoMovimiento = a.codigo_movimiento
        WHERE a.desc_renglon_asiento = %s
        ORDER BY cp.tipo, a.codigo_movimiento, a.id_pc
        """,
        (MARCA_REGEN,),
    )
    renglones = cur.fetchall()

    # Agregado por asiento (codigo_movimiento).
    asientos = {}
    for r in renglones:
        cm = r["codigo_movimiento"]
        a = asientos.setdefault(
            cm,
            {
                "codigo_movimiento": cm,
                "tipo": (r["tipo"] or "?"),
                "nro_comprobante": r["nro_comprobante"] or "",
                "fecha_cp": r["fecha_cp"],
                "nro_asiento": r["nro_asiento"],
                "id_ejercicio": r["id_ejercicio"],
                "fecha_asiento": r["fecha_asiento"],
                "concepto": r["id_concepto_asiento"],
                "desc_concepto": r["desc_concepto_asiento"] or "",
                "importe_comprobante": d(r["importe"]),
                "n_renglones": 0,
                "total_debe": Decimal("0"),
                "total_haber": Decimal("0"),
                "anulado": r["anulado"],
            },
        )
        a["n_renglones"] += 1
        a["total_debe"] += d(r["debe_asiento"])
        a["total_haber"] += d(r["haber_asiento"])

    for a in asientos.values():
        a["balanceado"] = "Si" if abs(a["total_debe"] - a["total_haber"]) <= Decimal("0.01") else "NO"

    # --- CSV detalle ---
    det_path = os.path.join(SALIDA_DIR, "REGISTRO_ASIENTOS_REGENERADOS_detalle.csv")
    with open(det_path, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f, delimiter=";")
        w.writerow([
            "tipo", "codigo_movimiento", "nro_comprobante", "fecha_comprobante",
            "nro_asiento", "id_ejercicio", "fecha_asiento", "concepto",
            "desc_concepto", "cod_pc", "cuenta", "naturaleza",
            "debe", "haber", "saldo_asiento", "anulado",
        ])
        for r in renglones:
            w.writerow([
                r["tipo"] or "?", r["codigo_movimiento"], r["nro_comprobante"] or "",
                fecha_es(r["fecha_cp"]), r["nro_asiento"], r["id_ejercicio"],
                fecha_es(r["fecha_asiento"]), r["id_concepto_asiento"],
                r["desc_concepto_asiento"] or "", r["cod_pc"] or "",
                (r["descrip_pc"] or "").strip(), (r["saldo_pc"] or "").strip(),
                str(d(r["debe_asiento"])), str(d(r["haber_asiento"])),
                str(d(r["saldo_asiento"])), r["anulado"],
            ])

    # --- CSV resumen ---
    res_path = os.path.join(SALIDA_DIR, "REGISTRO_ASIENTOS_REGENERADOS_resumen.csv")
    ordenados = sorted(asientos.values(), key=lambda a: (a["tipo"], str(a["codigo_movimiento"])))
    with open(res_path, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f, delimiter=";")
        w.writerow([
            "tipo", "codigo_movimiento", "nro_comprobante", "fecha_comprobante",
            "nro_asiento", "id_ejercicio", "fecha_asiento", "concepto",
            "desc_concepto", "n_renglones", "total_debe", "total_haber",
            "balanceado", "importe_comprobante", "anulado",
        ])
        for a in ordenados:
            w.writerow([
                a["tipo"], a["codigo_movimiento"], a["nro_comprobante"],
                fecha_es(a["fecha_cp"]), a["nro_asiento"], a["id_ejercicio"],
                fecha_es(a["fecha_asiento"]), a["concepto"], a["desc_concepto"],
                a["n_renglones"], str(a["total_debe"]), str(a["total_haber"]),
                a["balanceado"], str(a["importe_comprobante"]), a["anulado"],
            ])

    # --- Resumen por consola ---
    por_tipo = {}
    for a in asientos.values():
        t = por_tipo.setdefault(a["tipo"], {"asientos": 0, "renglones": 0,
                                            "debe": Decimal("0"), "haber": Decimal("0"),
                                            "desbal": 0})
        t["asientos"] += 1
        t["renglones"] += a["n_renglones"]
        t["debe"] += a["total_debe"]
        t["haber"] += a["total_haber"]
        if a["balanceado"] == "NO":
            t["desbal"] += 1

    print("=" * 78)
    print("REGISTRO DE ASIENTOS REGENERADOS (bug factura/OP sin asiento)")
    print("=" * 78)
    print(f"{'TIPO':<6}{'ASIENTOS':>10}{'RENGLONES':>12}{'TOTAL DEBE':>18}{'TOTAL HABER':>18}{'DESBAL':>8}")
    tot_a = tot_r = 0
    tot_d = tot_h = Decimal("0")
    tot_x = 0
    for t in sorted(por_tipo):
        x = por_tipo[t]
        print(f"{t:<6}{x['asientos']:>10}{x['renglones']:>12}{x['debe']:>18,.2f}{x['haber']:>18,.2f}{x['desbal']:>8}")
        tot_a += x["asientos"]; tot_r += x["renglones"]
        tot_d += x["debe"]; tot_h += x["haber"]; tot_x += x["desbal"]
    print("-" * 78)
    print(f"{'TOTAL':<6}{tot_a:>10}{tot_r:>12}{tot_d:>18,.2f}{tot_h:>18,.2f}{tot_x:>8}")
    print("=" * 78)
    print(f"Resumen por asiento : {res_path}")
    print(f"Detalle por renglón : {det_path}")

    conn.close()


if __name__ == "__main__":
    main()
