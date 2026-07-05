"""
Asiento contable automático del recibo (paridad ``generar_asiento_cont`` en json_recibo.php).
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal, InvalidOperation
from typing import Any, Dict, List, Tuple

from core.utils.administranet_types import to_int_or_none


def _to_decimal(value: Any, default: str = "0") -> Decimal:
    try:
        return Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError):
        return Decimal(default)


def _f(value: Decimal | float | int) -> float:
    return float(value)


def debe_generar_asiento_contable(cursor, *, id_pv: int) -> bool:
    cursor.execute(
        "SELECT cont FROM punto_venta WHERE id_punto_venta = %s LIMIT 1",
        [id_pv],
    )
    pv = cursor.fetchone()
    cursor.execute("SELECT activ_contabilidad FROM configuracion LIMIT 1")
    conf = cursor.fetchone()
    pv_cont = str((pv or {}).get("cont") or "").strip().lower() == "si"
    activ = str((conf or {}).get("activ_contabilidad") or "").strip().lower() == "si"
    return pv_cont and activ


def _id_pc_caja(cursor, id_caja: int) -> int | None:
    cursor.execute("SELECT id_pc FROM caja_abm WHERE id_caja = %s LIMIT 1", [id_caja])
    row = cursor.fetchone()
    return to_int_or_none(row.get("id_pc") if row else None)


def _id_pc_paramatriz(cursor, id_paramatriz: int) -> int | None:
    cursor.execute(
        "SELECT id_pc FROM cont_paramatriz WHERE id_paramatriz = %s LIMIT 1",
        [id_paramatriz],
    )
    row = cursor.fetchone()
    return to_int_or_none(row.get("id_pc") if row else None)


def _id_pc_cuenta_banco(cursor, cod_cuenta: int) -> int | None:
    cursor.execute(
        "SELECT id_pc FROM cuenta_banco WHERE codcuenta = %s LIMIT 1",
        [cod_cuenta],
    )
    row = cursor.fetchone()
    id_pc = to_int_or_none(row.get("id_pc") if row else None)
    if id_pc:
        return id_pc
    return _id_pc_paramatriz(cursor, 22)


def _armar_matriz_asiento(cursor, recibo: Dict[str, Any]) -> Tuple[List[Tuple[int, float, float]], float, float]:
    mat: List[Tuple[int, float, float]] = []

    efectivo = recibo.get("efectivo") if isinstance(recibo.get("efectivo"), dict) else {}
    if efectivo:
        id_caja = to_int_or_none(efectivo.get("idCaja"))
        id_pc = _id_pc_caja(cursor, id_caja) if id_caja else None
        if id_pc:
            pesos = _to_decimal(efectivo.get("pesos"))
            total_ef = _to_decimal(efectivo.get("total"))
            dolar_equiv = total_ef - pesos
            if pesos > Decimal("0"):
                mat.append((id_pc, _f(pesos), 0.0))
            if dolar_equiv > Decimal("0"):
                mat.append((id_pc, _f(dolar_equiv), 0.0))

    cheques = recibo.get("cheques") if isinstance(recibo.get("cheques"), dict) else {}
    if cheques and _to_decimal(cheques.get("total")) > Decimal("0"):
        id_caja = to_int_or_none(cheques.get("idCajaCheque"))
        id_pc = _id_pc_caja(cursor, id_caja) if id_caja else None
        if id_pc:
            mat.append((id_pc, _f(_to_decimal(cheques.get("total"))), 0.0))

    transf = recibo.get("transferencia") if isinstance(recibo.get("transferencia"), dict) else {}
    for item in transf.get("items") or []:
        cod = to_int_or_none(item.get("idCuentaBancaria"))
        importe = _to_decimal(item.get("total"))
        if cod and importe > Decimal("0"):
            id_pc = _id_pc_cuenta_banco(cursor, cod)
            if id_pc:
                mat.append((id_pc, _f(importe), 0.0))

    tarjetas_agg: Dict[int, Decimal] = {}
    tj_block = recibo.get("tarjeta") if isinstance(recibo.get("tarjeta"), dict) else {}
    id_pc_matriz = _id_pc_paramatriz(cursor, 5)
    for tj in (tj_block.get("listado") or {}).values():
        importe = _to_decimal(tj.get("importe"))
        if importe <= Decimal("0"):
            continue
        id_pc_tj = to_int_or_none(tj.get("idPc")) or id_pc_matriz
        if id_pc_tj is None:
            continue
        tarjetas_agg[id_pc_tj] = tarjetas_agg.get(id_pc_tj, Decimal("0")) + importe
    for id_pc_tj, importe in tarjetas_agg.items():
        mat.append((id_pc_tj, _f(importe), 0.0))

    ret_block = recibo.get("retencion") if isinstance(recibo.get("retencion"), dict) else {}
    for rt in (ret_block.get("lista") or {}).values():
        importe = _to_decimal(rt.get("monto"))
        cod_ret = to_int_or_none(rt.get("cod"))
        if importe <= Decimal("0") or cod_ret is None:
            continue
        cursor.execute(
            "SELECT id_pc FROM tipo_retencion_cli WHERE CodRetencion = %s LIMIT 1",
            [cod_ret],
        )
        row = cursor.fetchone()
        id_pc_ret = to_int_or_none(row.get("id_pc") if row else None)
        if id_pc_ret:
            mat.append((id_pc_ret, _f(importe), 0.0))

    saldo_favor = recibo.get("saldoAFavor") if isinstance(recibo.get("saldoAFavor"), dict) else {}
    total_favor = _to_decimal(saldo_favor.get("total"))
    id_pc_cliente = to_int_or_none(recibo.get("idPcCliente"))
    if total_favor > Decimal("0") and id_pc_cliente:
        mat.append((id_pc_cliente, _f(total_favor), 0.0))

    total_pago = Decimal("0")
    if efectivo:
        total_pago += _to_decimal(efectivo.get("total"))
    if cheques:
        total_pago += _to_decimal(cheques.get("total"))
    if transf:
        total_pago += _to_decimal(transf.get("total"))
    if tj_block:
        total_pago += _to_decimal(tj_block.get("total"))
    total_ret = _to_decimal((ret_block or {}).get("total"))
    total_recibo = total_pago + total_ret + total_favor

    if id_pc_cliente and total_recibo > Decimal("0"):
        mat.append((id_pc_cliente, 0.0, _f(total_recibo)))

    debe = sum(x[1] for x in mat)
    haber = sum(x[2] for x in mat)
    return mat, debe, haber


def generar_asiento_contable_recibo(
    cursor,
    *,
    recibo: Dict[str, Any],
    cod_mov: int,
    id_usuario: int,
) -> Dict[str, Any]:
    """Genera asiento en ``cont_asiento`` y actualiza saldos de ejercicio/periodo."""
    mat, debe, haber = _armar_matriz_asiento(cursor, recibo)
    if abs(debe - haber) > 0.02:
        return {
            "estado": "error",
            "variable": "debe <> haber",
            "sql": f"debe:{debe} haber:{haber} matriz:{mat}",
        }

    cursor.execute(
        "SELECT id_ejercicio, fecdesde_ejercicio, fechasta_ejercicio, nro_asiento_ejercicio "
        "FROM cont_ejercicio WHERE activo_ejercicio = 'Si' LIMIT 1"
    )
    ej = cursor.fetchone()
    if not ej:
        return {"estado": "error", "variable": "ejercicio", "sql": "Sin ejercicio activo."}

    id_ejercicio = int(ej["id_ejercicio"])
    cursor.execute(
        "SELECT id_periodo, fecdesde_periodo, fechasta_periodo "
        "FROM cont_periodo WHERE activo_periodo = 'Si' LIMIT 1"
    )
    per = cursor.fetchone()
    id_periodo = int(per["id_periodo"]) if per else 1

    if per:
        cursor.execute(
            "SELECT cerrado FROM cont_periodo WHERE id_periodo = %s AND id_ejercicio = %s LIMIT 1",
            [id_periodo, id_ejercicio],
        )
    else:
        cursor.execute(
            "SELECT cerrado FROM cont_ejercicio WHERE id_ejercicio = %s LIMIT 1",
            [id_ejercicio],
        )
    cerr = cursor.fetchone()
    if cerr and str(cerr.get("cerrado") or "").strip().lower() == "si":
        return {"estado": "error", "variable": "periodo_cerrado", "sql": "Periodo contable cerrado."}

    hoy = date.today()
    cursor.execute(
        "SELECT desc_concepto_asiento FROM cont_concepto_asiento WHERE id_concepto_asiento = 5 LIMIT 1"
    )
    concepto = cursor.fetchone()
    desc_concepto = (concepto or {}).get("desc_concepto_asiento") or "Recibo"

    nro_asiento = int(ej.get("nro_asiento_ejercicio") or 0)
    cursor.execute(
        "UPDATE cont_ejercicio SET Nro_asiento_ejercicio = %s WHERE id_ejercicio = %s",
        [nro_asiento + 1, id_ejercicio],
    )

    clase = str(recibo.get("clase") or "imputacion")
    nro_recibo = str(recibo.get("nroRecibo") or "")
    fecha_asiento = hoy

    for id_pc, debe_a, haber_a in mat:
        if debe_a == 0 and haber_a == 0:
            continue

        cursor.execute("SELECT saldo_pc FROM cont_pc WHERE id_pc = %s LIMIT 1", [id_pc])
        cuenta = cursor.fetchone() or {}
        saldo_pc_tipo = str(cuenta.get("saldo_pc") or "").strip()

        cursor.execute(
            """
            SELECT saldo_ejercicio_cta FROM cont_ejercicio_saldo_cta
            WHERE id_pc = %s AND id_ejercicio = %s LIMIT 1
            """,
            [id_pc, id_ejercicio],
        )
        saldo_ej = cursor.fetchone()
        saldo_cuenta = float((saldo_ej or {}).get("saldo_ejercicio_cta") or 0)

        if saldo_pc_tipo == "Deudor":
            saldo_cuenta = saldo_cuenta + debe_a - haber_a
            cursor.execute(
                """
                UPDATE cont_ejercicio_saldo_cta SET saldo_ejercicio_cta = %s
                WHERE id_pc = %s AND id_ejercicio = %s
                """,
                [saldo_cuenta, id_pc, id_ejercicio],
            )
        elif saldo_pc_tipo == "Acreedor":
            saldo_cuenta = saldo_cuenta - debe_a + haber_a
            cursor.execute(
                """
                UPDATE cont_ejercicio_saldo_cta SET saldo_ejercicio_cta = %s
                WHERE id_pc = %s AND id_ejercicio = %s
                """,
                [saldo_cuenta, id_pc, id_ejercicio],
            )

        cursor.execute(
            """
            SELECT saldo_periodo_cta FROM cont_periodo_saldo_cta
            WHERE id_pc = %s AND id_ejercicio = %s AND id_periodo = %s LIMIT 1
            """,
            [id_pc, id_ejercicio, id_periodo],
        )
        saldo_per = cursor.fetchone()
        if saldo_per:
            saldo_per_val = float(saldo_per.get("saldo_periodo_cta") or 0)
            if saldo_pc_tipo == "Deudor":
                saldo_per_val = saldo_per_val + debe_a - haber_a
            elif saldo_pc_tipo == "Acreedor":
                saldo_per_val = saldo_per_val - debe_a + haber_a
            cursor.execute(
                """
                UPDATE cont_periodo_saldo_cta SET saldo_periodo_cta = %s
                WHERE id_pc = %s AND id_ejercicio = %s AND id_periodo = %s
                """,
                [saldo_per_val, id_pc, id_ejercicio, id_periodo],
            )

        cursor.execute(
            """
            INSERT INTO cont_asiento (
                codigo_movimiento, nro_asiento, id_periodo, id_ejercicio, saldo_asiento,
                fecha_asiento, debe_asiento, haber_asiento, id_pc, desc_concepto_asiento,
                id_concepto_asiento, balanceado_asiento, id_usuario, desc_asiento
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 5, 'Si', %s, %s)
            """,
            [
                cod_mov,
                str(nro_asiento),
                id_periodo,
                id_ejercicio,
                saldo_cuenta,
                fecha_asiento,
                debe_a,
                haber_a,
                id_pc,
                desc_concepto,
                id_usuario,
                f"Recibo por {clase} - Nro Comp. REC - {nro_recibo}",
            ],
        )

    return {"estado": "ok", "asiento": nro_asiento}
