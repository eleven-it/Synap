#!/usr/bin/env python3
"""Reconstrucción/validación de asientos contables de compras y pagos (AdministraNET).

Uso (dentro del contenedor Synap_app):
    docker exec Synap_app python legacy_db/scripts/cont_reconstruccion_compras_pagos.py validate-fa
    docker exec Synap_app python legacy_db/scripts/cont_reconstruccion_compras_pagos.py validate-op
    docker exec Synap_app python legacy_db/scripts/cont_reconstruccion_compras_pagos.py dryrun-missing
    docker exec Synap_app python legacy_db/scripts/cont_reconstruccion_compras_pagos.py apply-missing   # ESCRIBE

Modos de LECTURA (validate-*, dryrun-missing): reconstruyen la composición del
asiento que VB6 (PFactura/OrdenPago -> generar_asiento_cont) hubiera generado, a
partir de las tablas PERSISTIDAS (los temporales por usuario originales ya no existen),
y la comparan contra cont_asiento para medir fidelidad.

Modo de ESCRITURA (apply-missing): regenera los asientos faltantes en cont_asiento
(reusa CodigoMovimiento, nro_asiento nuevo, fecha original, concepto 3/7),
idempotente y transaccional por asiento. Los renglones quedan marcados en
desc_renglon_asiento con MARCA_REGEN para poder localizarlos/revertirlos.

Referencias de lógica: docs/general/AUDITORIA_IMPUTACION_CONTABILIDAD_VB6.md (H51-H53)
y las specs del change openspec/changes/contabilidad-auditoria-recalculo/.
"""
import os
import sys
from collections import defaultdict
from decimal import Decimal, ROUND_HALF_UP

import MySQLdb

DB = dict(
    host=os.environ.get("DB_HOST", "190.15.214.142"),
    port=int(os.environ.get("DB_PORT", "3306")),
    user=os.environ.get("DB_USER", "administranet"),
    passwd=os.environ.get("DB_PASSWORD", "a7v8xx0805"),
    db=os.environ.get("DB_NAME", "administranet89"),
    charset="latin1",
)

TIPOS_FACTURA = ("FA", "FC")
Q2 = Decimal("0.01")

# Regeneración (apply). Concepto contable por tipo de comprobante.
CONCEPTO = {"FA": 3, "FC": 3, "OP": 7}
DESC_CONCEPTO = {3: "Compra", 7: "Pago"}
# Cuenta de diferencias/redondeo (cont_pc.descrip_pc='Redondeo', codjer 410241--).
REDONDEO_PC = 300
# Ajuste tipo Balancea_asiento: se imputa a Redondeo un desbalance residual
# menor o igual a este umbral; por encima se bloquea (no debería haber).
UMBRAL_REDONDEO = Decimal("1.00")
# Marca de trazabilidad en cada renglón regenerado (permite localizar/revertir).
MARCA_REGEN = "REGEN auditoria (bug factura/OP sin asiento)"
# Gating REC-18 alineado a REC-20: solo PV con cont='Si' (no sucursales.cont).
_JOIN_PV_CONT = "JOIN punto_venta pv ON pv.id_punto_venta = cp.id_pv"
_FILTRO_PV_CONT = " AND COALESCE(pv.cont,'No')='Si' "


def d(v):
    if v is None:
        return Decimal("0")
    return Decimal(str(v))


def r2(v):
    return d(v).quantize(Q2, rounding=ROUND_HALF_UP)


class Repo:
    def __init__(self, conn):
        self.c = conn
        self._matriz = {}
        self._prov_pc = {}
        self._gasto_pc = {}
        self._art = {}
        self._caja = {}
        self._impuesto_pc = {}
        self._deuda_pc = {}
        self._percepcion_pc = {}
        self._cuenta_banco_pc = {}
        self._ejercicio = {}
        self._periodo = {}
        self._saldo_pc = {}

    def cur(self):
        return self.c.cursor(MySQLdb.cursors.DictCursor)

    def matriz(self, idm):
        if idm not in self._matriz:
            cur = self.cur()
            cur.execute("SELECT id_pc FROM cont_paramatriz WHERE id_paramatriz=%s", (idm,))
            row = cur.fetchone()
            self._matriz[idm] = (row["id_pc"] if row else None)
        return self._matriz[idm]

    def proveedor_pc(self, codigo):
        if codigo not in self._prov_pc:
            cur = self.cur()
            cur.execute("SELECT id_pc FROM proveedor WHERE codigo=%s", (codigo,))
            rows = cur.fetchall()
            self._prov_pc[codigo] = (rows[0]["id_pc"] if len(rows) == 1 else None)
        return self._prov_pc[codigo]

    def gasto_pc(self, codigo):
        if codigo not in self._gasto_pc:
            cur = self.cur()
            cur.execute("SELECT id_pc FROM gastos WHERE Codigo=%s", (codigo,))
            row = cur.fetchone()
            self._gasto_pc[codigo] = (row["id_pc"] if row else None)
        return self._gasto_pc[codigo]

    def articulo(self, idart):
        if idart not in self._art:
            cur = self.cur()
            cur.execute("SELECT idart,id_pc_comp,cod_gasto FROM articulo WHERE idart=%s", (idart,))
            self._art[idart] = cur.fetchone()
        return self._art[idart]

    def impuesto_pc(self, id_impuesto):
        if id_impuesto not in self._impuesto_pc:
            cur = self.cur()
            cur.execute("SELECT id_pc_deuda FROM impuesto WHERE id_impuesto=%s", (id_impuesto,))
            row = cur.fetchone()
            self._impuesto_pc[id_impuesto] = row["id_pc_deuda"] if row else None
        return self._impuesto_pc[id_impuesto]

    def deuda_pc(self, id_deuda):
        if id_deuda not in self._deuda_pc:
            cur = self.cur()
            cur.execute("SELECT id_pc FROM deuda_abm WHERE id_deuda_abm=%s", (id_deuda,))
            row = cur.fetchone()
            self._deuda_pc[id_deuda] = row["id_pc"] if row else None
        return self._deuda_pc[id_deuda]

    def percepcion_pc(self, id_percepcion):
        if id_percepcion not in self._percepcion_pc:
            cur = self.cur()
            cur.execute(
                "SELECT id_pc FROM percepcion_abm WHERE id_percepcion_abm=%s",
                (id_percepcion,),
            )
            row = cur.fetchone()
            self._percepcion_pc[id_percepcion] = row["id_pc"] if row else None
        return self._percepcion_pc[id_percepcion]

    def caja_pc(self, id_caja, dolares=False):
        clave = (id_caja, dolares)
        if clave not in self._caja:
            campo = "id_pc_dolares" if dolares else "id_pc"
            cur = self.cur()
            cur.execute(f"SELECT {campo} id_pc FROM caja_abm WHERE id_caja=%s", (id_caja,))
            row = cur.fetchone()
            self._caja[clave] = row["id_pc"] if row else None
        return self._caja[clave]

    def cuenta_banco_pc(self, codigo):
        if codigo not in self._cuenta_banco_pc:
            cur = self.cur()
            cur.execute("SELECT id_pc FROM cuenta_banco WHERE CodCuenta=%s", (codigo,))
            row = cur.fetchone()
            self._cuenta_banco_pc[codigo] = row["id_pc"] if row else None
        return self._cuenta_banco_pc[codigo]

    def saldo_pc(self, id_pc):
        """Naturaleza contable de la cuenta: 'Deudor' / 'Acreedor' (o None)."""
        if id_pc not in self._saldo_pc:
            cur = self.cur()
            cur.execute("SELECT saldo_pc FROM cont_pc WHERE id_pc=%s", (id_pc,))
            row = cur.fetchone()
            valor = (row["saldo_pc"] if row else None) or ""
            self._saldo_pc[id_pc] = valor.strip() or None
        return self._saldo_pc[id_pc]

    def ejercicio(self, fecha):
        if fecha not in self._ejercicio:
            cur = self.cur()
            cur.execute(
                """SELECT id_ejercicio, descripcion_ejercicio, cerrado
                   FROM cont_ejercicio
                   WHERE %s BETWEEN fecdesde_ejercicio AND fechasta_ejercicio
                   ORDER BY id_ejercicio DESC LIMIT 1""",
                (fecha,),
            )
            self._ejercicio[fecha] = cur.fetchone()
        return self._ejercicio[fecha]

    def periodo(self, id_ejercicio, fecha):
        clave = (id_ejercicio, fecha)
        if clave not in self._periodo:
            cur = self.cur()
            cur.execute(
                """SELECT id_periodo, descripcion_periodo, cerrado
                   FROM cont_periodo
                   WHERE id_ejercicio=%s
                     AND %s BETWEEN fecdesde_periodo AND fechasta_periodo
                   ORDER BY id_periodo DESC LIMIT 1""",
                (id_ejercicio, fecha),
            )
            self._periodo[clave] = cur.fetchone()
        return self._periodo[clave]


def add(renglones, id_pc, debe=0, haber=0):
    if id_pc is None:
        renglones.setdefault("_ERR_", []).append(("cuenta_nula", str(debe), str(haber)))
        return
    key = int(id_pc)
    renglones[key][0] += d(debe)
    renglones[key][1] += d(haber)


def reconstruir_factura(repo, cab):
    """Devuelve (renglones_dict{id_pc:[debe,haber]}, errores:list)."""
    renglones = defaultdict(lambda: [Decimal("0"), Decimal("0")])
    errores = []
    codmov = cab["CodigoMovimiento"]

    # 1) Neto de mercadería/gasto (DEBE) desde stock persistido
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
        if art and art["id_pc_comp"] not in (None, 0):
            cuenta = art["id_pc_comp"]
        elif art and art["cod_gasto"] not in (None, 0):
            cuenta = repo.gasto_pc(art["cod_gasto"])
            if cuenta is None:
                cuenta = repo.matriz(24)
        else:
            cuenta = repo.matriz(13)
        add(renglones, cuenta, debe=f["PrecioNetoxR"])

    # 2) IVA crédito fiscal (DEBE)
    for campo, idm in (("IVA1", 10), ("IVA2", 11), ("IVA3", 12), ("sobretasa_iva", 50)):
        val = d(cab.get(campo))
        if val > 0:
            add(renglones, repo.matriz(idm), debe=val)
    # 3-6) impuestos/percepciones simples (DEBE)
    for campo, idm in (("impuesto_interno", 6), ("OtrosImp", 15), ("PercepIVA", 16), ("PercepGan", 17)):
        val = d(cab.get(campo))
        if val > 0:
            add(renglones, repo.matriz(idm), debe=val)
    # 7) Percepciones IIBB por jurisdicción (DEBE) desde percep_prov persistido
    cur.execute(
        """SELECT p.importe_percep, pr.id_pc
           FROM percep_prov p LEFT JOIN provincia pr ON pr.codProvincia = p.id_jurisdiccion
           WHERE p.codigo_movimiento=%s AND COALESCE(p.anulado,'No')<>'Si'""",
        (codmov,),
    )
    for f in cur.fetchall():
        add(renglones, f["id_pc"], debe=f["importe_percep"])

    # 8) Descuento global obtenido (HABER) -> matriz 20
    desc = d(cab.get("TotalDesc"))
    if desc > 0:
        add(renglones, repo.matriz(20), haber=desc)

    # 9) Contrapartida (HABER): contado -> caja ; cta cte -> proveedor / matriz 28
    importe_total = d(cab.get("ImporteCompra"))
    if cab.get("id_condcompra") == 1:
        errores.append("contado_requiere_caja")  # caja no resoluble de forma inequívoca
    else:
        cuenta_prov = repo.proveedor_pc(cab["Codigo"])
        if cuenta_prov is None:
            cuenta_prov = repo.matriz(28)
        add(renglones, cuenta_prov, haber=importe_total)

    return renglones, errores


def reconstruir_op(repo, cab):
    """Reconstruye el asiento OP desde los movimientos persistidos."""
    renglones = defaultdict(lambda: [Decimal("0"), Decimal("0")])
    errores = []
    codmov = cab["CodigoMovimiento"]
    tipo_op = (cab.get("TipoOP") or "").strip().lower()
    cur = repo.cur()

    # 1) Egresos y percepciones (DEBE).
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
            add(renglones, None, debe=fila["importe_oe"])
            continue
        add(renglones, cuenta, debe=importe)

    # 2) Contrapartida proveedor (DEBE) para pagos a cuenta o imputaciones.
    if tipo_op in ("a cuenta", "imputacion"):
        add(renglones, repo.proveedor_pc(cab["Codigo"]), debe=cab.get("TotalOP"))
    elif tipo_op != "egreso":
        errores.append(f"tipo_op_desconocido:{tipo_op}")

    # 3) Retenciones (HABER).
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
            add(renglones, repo.matriz(matriz), haber=fila["Importe"])

    # 4) Efectivo desde caja. El origen persistido identifica la cuenta caja.
    cur.execute(
        """SELECT egreso, moneda, id_caja_abm_origen
           FROM caja
           WHERE codigo_movimiento=%s AND COALESCE(anulado,'No')<>'Si'
             AND COALESCE(egreso,0)<>0
             AND id_chequetercero IS NULL""",
        (codmov,),
    )
    for fila in cur.fetchall():
        es_dolar = (fila["moneda"] or "").strip().lower() in ("dolar", "dólar", "usd")
        if es_dolar:
            errores.append("efectivo_dolares_persistido")
        add(
            renglones,
            repo.caja_pc(fila["id_caja_abm_origen"], dolares=es_dolar),
            haber=fila["egreso"],
        )

    # 5) Cheques propios y de terceros (HABER).
    cur.execute(
        """SELECT Importe FROM chequepropio
           WHERE CodigoMovimientoOP=%s AND COALESCE(Anulado,'No')<>'Si'""",
        (codmov,),
    )
    for fila in cur.fetchall():
        add(renglones, repo.matriz(32), haber=fila["Importe"])

    cur.execute(
        """SELECT Importe, id_caja FROM chequetercero
           WHERE CodigoMovimientoOP=%s AND COALESCE(Anulado,'No')<>'Si'""",
        (codmov,),
    )
    for fila in cur.fetchall():
        cuenta = repo.caja_pc(fila["id_caja"]) if fila["id_caja"] else None
        add(renglones, cuenta or repo.matriz(31), haber=fila["Importe"])

    # 6) Transferencias (HABER).
    cur.execute(
        """SELECT importe_transf, id_cuentabancaria FROM transferencia
           WHERE codigo_movimiento=%s AND COALESCE(anulado,'No')<>'Si'""",
        (codmov,),
    )
    for fila in cur.fetchall():
        cuenta = repo.cuenta_banco_pc(fila["id_cuentabancaria"])
        add(renglones, cuenta or repo.matriz(42), haber=fila["importe_transf"])

    return renglones, errores


def asiento_real(repo, codmov):
    cur = repo.cur()
    cur.execute(
        """SELECT id_pc, SUM(COALESCE(debe_asiento,0)) debe, SUM(COALESCE(haber_asiento,0)) haber
           FROM cont_asiento WHERE codigo_movimiento=%s AND COALESCE(anulado,'No')<>'Si'
           GROUP BY id_pc""",
        (codmov,),
    )
    return {int(x["id_pc"]): [d(x["debe"]), d(x["haber"])] for x in cur.fetchall()}


def neto(renglones):
    return {k: r2(v[0] - v[1]) for k, v in renglones.items() if k != "_ERR_"}


def comparar(recon, real):
    nr, na = neto(recon), real and {k: r2(v[0] - v[1]) for k, v in real.items()}
    cuentas = set(nr) | set(na)
    difs = []
    for k in cuentas:
        a = nr.get(k, Decimal("0"))
        b = na.get(k, Decimal("0"))
        if abs(a - b) > Q2:
            difs.append((k, str(a), str(b)))
    return difs


def validate(mode):
    conn = MySQLdb.connect(**DB)
    repo = Repo(conn)
    cur = repo.cur()
    cur.execute(
        f"""SELECT cp.* FROM cuentaproveedor cp
           {_JOIN_PV_CONT}
           WHERE COALESCE(cp.Anulado,'No')<>'Si'{_FILTRO_PV_CONT}
             AND cp.TipoComprobante IN %s AND cp.CodigoMovimiento<>0
             AND EXISTS (SELECT 1 FROM cont_asiento ca WHERE ca.codigo_movimiento=cp.CodigoMovimiento)""",
        (TIPOS_FACTURA,),
    )
    cabs = cur.fetchall()
    total = len(cabs)
    ok = 0
    contado = 0
    remap = 0          # misma plata total debe/haber, solo cambia la cuenta (deriva historica de config)
    estructural = []   # diferencia real de importes/estructura
    for cab in cabs:
        recon, errores = reconstruir_factura(repo, cab)
        if "contado_requiere_caja" in errores:
            contado += 1
            continue
        real = asiento_real(repo, cab["CodigoMovimiento"])
        difs = comparar(recon, real)
        if not difs and "_ERR_" not in recon:
            ok += 1
            continue
        # clasificar: si los totales debe/haber coinciden, es remapeo de cuenta (benigno)
        rd = r2(sum((v[0] for v in recon.values() if isinstance(v, list)), Decimal("0")))
        rh = r2(sum((v[1] for v in recon.values() if isinstance(v, list)), Decimal("0")))
        ad = r2(sum((v[0] for v in real.values()), Decimal("0")))
        ah = r2(sum((v[1] for v in real.values()), Decimal("0")))
        if "_ERR_" not in recon and abs(rd - ad) <= Q2 and abs(rh - ah) <= Q2:
            remap += 1
        else:
            estructural.append((cab["CodigoMovimiento"], cab["TipoComprobante"], difs, errores, str(rd), str(ad), str(rh), str(ah)))
    print(f"[validate-fa] universo con asiento: {total}")
    print(f"  match exacto (misma cuenta):        {ok}")
    print(f"  remap (misma plata, cuenta movida): {remap}")
    print(f"  contado (caja no resuelta):         {contado}")
    print(f"  ESTRUCTURAL (revisar):              {len(estructural)}")
    fidel = ok + remap
    print(f"  => fidelidad de importes: {fidel}/{total - contado} ({(100.0*fidel/max(total-contado,1)):.1f}%)")
    for cm, tipo, difs, err, rd, ad, rh, ah in estructural[:20]:
        print(f"   - cm={cm} {tipo} recon(D={rd},H={rh}) real(D={ad},H={ah}) err={err} difs={difs[:6]}")
    conn.close()


def validate_op():
    conn = MySQLdb.connect(**DB)
    repo = Repo(conn)
    cur = repo.cur()
    cur.execute(
        f"""SELECT cp.* FROM cuentaproveedor cp
           {_JOIN_PV_CONT}
           WHERE COALESCE(cp.Anulado,'No')<>'Si'{_FILTRO_PV_CONT}
             AND cp.TipoComprobante='OP' AND cp.CodigoMovimiento<>0
             AND EXISTS (SELECT 1 FROM cont_asiento ca WHERE ca.codigo_movimiento=cp.CodigoMovimiento)"""
    )
    cabs = cur.fetchall()
    total = len(cabs)
    ok = 0
    remap = 0
    con_error = 0
    estructural = []
    for cab in cabs:
        recon, errores = reconstruir_op(repo, cab)
        real = asiento_real(repo, cab["CodigoMovimiento"])
        difs = comparar(recon, real)
        if not difs and "_ERR_" not in recon and not errores:
            ok += 1
            continue
        rd = r2(sum((v[0] for v in recon.values() if isinstance(v, list)), Decimal("0")))
        rh = r2(sum((v[1] for v in recon.values() if isinstance(v, list)), Decimal("0")))
        ad = r2(sum((v[0] for v in real.values()), Decimal("0")))
        ah = r2(sum((v[1] for v in real.values()), Decimal("0")))
        if "_ERR_" in recon:
            con_error += 1
        if "_ERR_" not in recon and not errores and abs(rd - ad) <= Q2 and abs(rh - ah) <= Q2:
            remap += 1
        else:
            estructural.append(
                (
                    cab["CodigoMovimiento"],
                    cab.get("TipoOP"),
                    difs,
                    errores,
                    str(rd),
                    str(ad),
                    str(rh),
                    str(ah),
                )
            )
    print(f"[validate-op] universo con asiento: {total}")
    print(f"  match exacto (misma cuenta):        {ok}")
    print(f"  remap (misma plata, cuenta movida): {remap}")
    print(f"  ESTRUCTURAL (revisar):              {len(estructural)}")
    print(f"  con _ERR_ (cuenta no resuelta):     {con_error}")
    fidel = ok + remap
    print(f"  => fidelidad de importes: {fidel}/{total} ({(100.0*fidel/max(total,1)):.1f}%)")
    for cm, tipo, difs, err, rd, ad, rh, ah in estructural[:20]:
        print(f"   - cm={cm} {tipo} recon(D={rd},H={rh}) real(D={ad},H={ah}) err={err} difs={difs[:6]}")
    conn.close()


def dryrun_missing():
    """Simula la regeneración de comprobantes sin asiento, sin escribir datos."""
    conn = MySQLdb.connect(**DB)
    repo = Repo(conn)
    cur = repo.cur()
    cur.execute(
        f"""SELECT cp.* FROM cuentaproveedor cp
           {_JOIN_PV_CONT}
           WHERE COALESCE(cp.Anulado,'No')<>'Si'{_FILTRO_PV_CONT}
             AND cp.TipoComprobante IN ('FA','FC','OP') AND cp.CodigoMovimiento<>0
             AND NOT EXISTS (
                 SELECT 1 FROM cont_asiento ca
                 WHERE ca.codigo_movimiento=cp.CodigoMovimiento
                   AND ca.codigo_movimiento<>0
             )"""
    )
    cabs = cur.fetchall()
    por_tipo = defaultdict(int)
    clasificacion = defaultdict(int)
    por_ejercicio = defaultdict(lambda: Decimal("0"))
    impacto = defaultdict(lambda: [Decimal("0"), Decimal("0")])
    observaciones_periodo = defaultdict(int)
    bloqueados = []

    for cab in cabs:
        tipo = cab["TipoComprobante"]
        por_tipo[tipo] += 1
        if tipo in TIPOS_FACTURA:
            renglones, errores = reconstruir_factura(repo, cab)
        else:
            renglones, errores = reconstruir_op(repo, cab)

        debe = r2(sum((v[0] for v in renglones.values() if isinstance(v, list)), Decimal("0")))
        haber = r2(sum((v[1] for v in renglones.values() if isinstance(v, list)), Decimal("0")))
        desbalance = abs(debe - haber)
        fecha = cab.get("Fecha")
        ejercicio = repo.ejercicio(fecha) if fecha else None
        periodo = repo.periodo(ejercicio["id_ejercicio"], fecha) if ejercicio else None

        if not fecha:
            observaciones_periodo["sin_fecha_comprobante"] += 1
        elif not ejercicio:
            observaciones_periodo["sin_ejercicio_para_periodo"] += 1
        elif not periodo:
            observaciones_periodo["sin_periodo"] += 1
        elif periodo["cerrado"] == "Si":
            observaciones_periodo["periodo_cerrado"] += 1

        if "_ERR_" in renglones:
            estado = "bloqueado_cuenta_nula"
            motivo = renglones["_ERR_"]
        elif "contado_requiere_caja" in errores:
            estado = "bloqueado_contado"
            motivo = errores
        elif desbalance > Q2:
            estado = "bloqueado_desbalance"
            motivo = errores or f"desbalance={desbalance}"
        elif not ejercicio:
            estado = "bloqueado_sin_ejercicio"
            motivo = "fecha_fuera_de_ejercicio"
        elif ejercicio["cerrado"] == "Si":
            estado = "bloqueado_ejercicio_cerrado"
            motivo = ejercicio["descripcion_ejercicio"]
        else:
            estado = "regenerable"
            motivo = None

        clasificacion[estado] += 1
        if estado == "regenerable":
            id_ejercicio = int(ejercicio["id_ejercicio"])
            por_ejercicio[(id_ejercicio, ejercicio["descripcion_ejercicio"])] += debe
            for id_pc, valores in renglones.items():
                if id_pc == "_ERR_":
                    continue
                impacto[id_pc][0] += valores[0]
                impacto[id_pc][1] += valores[1]
        else:
            bloqueados.append(
                (
                    cab["CodigoMovimiento"],
                    tipo,
                    fecha,
                    estado,
                    motivo,
                    str(debe),
                    str(haber),
                    str(desbalance),
                )
            )

    print(f"[dryrun-missing] huérfanos linkables: {len(cabs)}")
    print("  por tipo: " + " | ".join(f"{tipo}={por_tipo[tipo]}" for tipo in ("FA", "FC", "OP")))
    print("  clasificación:")
    for estado in (
        "regenerable",
        "bloqueado_cuenta_nula",
        "bloqueado_contado",
        "bloqueado_desbalance",
        "bloqueado_sin_ejercicio",
        "bloqueado_ejercicio_cerrado",
    ):
        print(f"    {estado}: {clasificacion[estado]}")

    total_regenerable = r2(sum(por_ejercicio.values(), Decimal("0")))
    print(f"  total $ regenerable (debe): {total_regenerable}")
    print("  por ejercicio:")
    for (id_ejercicio, descripcion), total in sorted(por_ejercicio.items()):
        print(f"    ejercicio={id_ejercicio} {descripcion}: {r2(total)}")

    if observaciones_periodo:
        print("  observaciones de período:")
        for motivo, cantidad in sorted(observaciones_periodo.items()):
            print(f"    {motivo}: {cantidad}")

    print("  impacto por cuenta (top 20 por neto absoluto):")
    cuentas = sorted(
        impacto.items(),
        key=lambda item: abs(item[1][0] - item[1][1]),
        reverse=True,
    )
    for id_pc, (debe, haber) in cuentas[:20]:
        print(f"    id_pc={id_pc} debe={r2(debe)} haber={r2(haber)} neto={r2(debe - haber)}")

    print("  bloqueados (hasta 20):")
    for cm, tipo, fecha, estado, motivo, debe, haber, desbalance in bloqueados[:20]:
        print(
            f"    cm={cm} tipo={tipo} fecha={fecha} motivo={estado} "
            f"detalle={motivo} D={debe} H={haber} desbalance={desbalance}"
        )
    conn.close()


def _asiento_ya_existe(repo, codmov):
    cur = repo.cur()
    cur.execute(
        "SELECT COUNT(*) n FROM cont_asiento WHERE codigo_movimiento=%s AND codigo_movimiento<>0",
        (codmov,),
    )
    return cur.fetchone()["n"] > 0


def _saldo_inicial_ejercicio(repo, id_pc, id_ejercicio):
    """Saldo acumulado actual de la cuenta en el ejercicio (semilla del saldo corrido)."""
    cur = repo.cur()
    cur.execute(
        "SELECT saldo_ejercicio_cta FROM cont_ejercicio_saldo_cta WHERE id_pc=%s AND id_ejercicio=%s",
        (id_pc, id_ejercicio),
    )
    row = cur.fetchone()
    return d(row["saldo_ejercicio_cta"]) if row else Decimal("0")


def apply_missing():
    """Regenera (ESCRIBE) los asientos faltantes de compras/pagos.

    - Reutiliza el CodigoMovimiento del comprobante y asigna un nro_asiento nuevo
      del contador cont_ejercicio.nro_asiento_ejercicio (con SELECT ... FOR UPDATE).
    - Fecha = fecha original; concepto 3 (Compra) / 7 (Pago); id_periodo NULL
      (cont_periodo sin filas). saldo_asiento = saldo corrido de la cuenta.
    - Idempotente: omite comprobantes que ya tengan asiento.
    - Desbalance residual <= UMBRAL_REDONDEO se imputa a la cuenta Redondeo
      (ajuste tipo Balancea_asiento); por encima se bloquea.
    - Transacción por asiento (InnoDB): confirma cada uno; ante error, rollback y sigue.
    NO recalcula los saldos totales: eso lo hace la fase rebuild-saldos.
    """
    conn = MySQLdb.connect(**DB)
    conn.autocommit(False)
    repo = Repo(conn)
    cur = repo.cur()
    cur.execute(
        f"""SELECT cp.* FROM cuentaproveedor cp
           {_JOIN_PV_CONT}
           WHERE COALESCE(cp.Anulado,'No')<>'Si'{_FILTRO_PV_CONT}
             AND cp.TipoComprobante IN ('FA','FC','OP') AND cp.CodigoMovimiento<>0
             AND NOT EXISTS (
                 SELECT 1 FROM cont_asiento ca
                 WHERE ca.codigo_movimiento=cp.CodigoMovimiento
                   AND ca.codigo_movimiento<>0
             )"""
    )
    cabs = cur.fetchall()
    print(f"[apply-missing] huérfanos a procesar: {len(cabs)}")

    saldos_run = {}          # (id_pc, id_ejercicio) -> saldo corrido en memoria
    insertados = 0           # asientos (comprobantes) insertados
    renglones_ins = 0        # filas cont_asiento insertadas
    ajustados = 0            # asientos con ajuste de redondeo aplicado
    omitidos = 0             # ya tenían asiento (idempotencia)
    bloqueados = []          # (cm, tipo, motivo)

    for cab in cabs:
        codmov = cab["CodigoMovimiento"]
        tipo = cab["TipoComprobante"]
        fecha = cab.get("Fecha")
        try:
            if _asiento_ya_existe(repo, codmov):
                omitidos += 1
                continue

            if tipo in TIPOS_FACTURA:
                renglones, errores = reconstruir_factura(repo, cab)
            else:
                renglones, errores = reconstruir_op(repo, cab)

            if "_ERR_" in renglones:
                bloqueados.append((codmov, tipo, f"cuenta_nula:{renglones['_ERR_']}"))
                continue
            if "contado_requiere_caja" in errores:
                bloqueados.append((codmov, tipo, "contado_sin_caja"))
                continue

            debe = r2(sum((v[0] for v in renglones.values()), Decimal("0")))
            haber = r2(sum((v[1] for v in renglones.values()), Decimal("0")))
            dif = r2(debe - haber)
            ajuste = False
            if abs(dif) > Q2:
                if abs(dif) <= UMBRAL_REDONDEO:
                    if dif > 0:
                        add(renglones, REDONDEO_PC, haber=dif)
                    else:
                        add(renglones, REDONDEO_PC, debe=-dif)
                    ajuste = True
                else:
                    bloqueados.append((codmov, tipo, f"desbalance={dif}"))
                    continue

            ejercicio = repo.ejercicio(fecha) if fecha else None
            if not ejercicio:
                bloqueados.append((codmov, tipo, "sin_ejercicio_para_fecha"))
                continue
            if ejercicio["cerrado"] == "Si":
                bloqueados.append((codmov, tipo, "ejercicio_cerrado"))
                continue
            id_ejercicio = int(ejercicio["id_ejercicio"])

            # Numeración: bloqueo la fila del ejercicio y tomo/actualizo el contador.
            wcur = conn.cursor(MySQLdb.cursors.DictCursor)
            wcur.execute(
                "SELECT nro_asiento_ejercicio FROM cont_ejercicio WHERE id_ejercicio=%s FOR UPDATE",
                (id_ejercicio,),
            )
            nro_asiento = int(wcur.fetchone()["nro_asiento_ejercicio"])
            wcur.execute(
                "UPDATE cont_ejercicio SET nro_asiento_ejercicio=%s WHERE id_ejercicio=%s",
                (nro_asiento + 1, id_ejercicio),
            )

            concepto = CONCEPTO[tipo]
            desc_concepto = DESC_CONCEPTO[concepto]
            nro_comp = cab.get("NroComprobante")
            if tipo == "OP":
                desc_asiento = f"{(cab.get('TipoOP') or '').strip()} - Nro Comp. OP - {nro_comp}"
            else:
                desc_asiento = f"Compra - Nro Comp. {nro_comp}"

            # Inserto un renglón por cuenta (orden estable por id_pc).
            for id_pc in sorted(k for k in renglones if k != "_ERR_"):
                vdebe, vhaber = renglones[id_pc]
                vdebe, vhaber = r2(vdebe), r2(vhaber)
                if vdebe == 0 and vhaber == 0:
                    continue
                natur = repo.saldo_pc(id_pc) or "Deudor"
                clave = (id_pc, id_ejercicio)
                if clave not in saldos_run:
                    saldos_run[clave] = _saldo_inicial_ejercicio(repo, id_pc, id_ejercicio)
                if natur == "Acreedor":
                    saldos_run[clave] += (vhaber - vdebe)
                else:
                    saldos_run[clave] += (vdebe - vhaber)
                saldo_asiento = saldos_run[clave].quantize(Q2, rounding=ROUND_HALF_UP)

                wcur.execute(
                    """INSERT INTO cont_asiento
                       (nro_asiento, fecha_asiento, id_ejercicio, id_periodo,
                        codigo_movimiento, debe_asiento, haber_asiento, saldo_asiento,
                        id_pc, desc_renglon_asiento, desc_concepto_asiento,
                        id_concepto_asiento, balanceado_asiento, id_usuario,
                        desc_asiento, tipo_asiento, anulado)
                       VALUES (%s,%s,%s,NULL,%s,%s,%s,%s,%s,%s,%s,%s,'Si',NULL,%s,'Proceso','No')""",
                    (
                        nro_asiento, fecha, id_ejercicio, codmov,
                        str(vdebe), str(vhaber), str(saldo_asiento), id_pc,
                        MARCA_REGEN, desc_concepto, concepto, desc_asiento,
                    ),
                )
                renglones_ins += 1

            conn.commit()
            insertados += 1
            if ajuste:
                ajustados += 1
        except Exception as exc:  # noqa: BLE001
            conn.rollback()
            bloqueados.append((codmov, tipo, f"error:{exc}"))

    print(f"  asientos insertados:       {insertados}")
    print(f"  renglones insertados:      {renglones_ins}")
    print(f"  con ajuste de redondeo:    {ajustados}")
    print(f"  omitidos (ya tenían):      {omitidos}")
    print(f"  bloqueados:                {len(bloqueados)}")
    for cm, tipo, motivo in bloqueados[:30]:
        print(f"    cm={cm} tipo={tipo} :: {motivo}")
    conn.close()


def _saldos_derivados(repo):
    """Saldo por (id_pc, id_ejercicio) = suma firmada de TODAS las filas del diario.

    Modelo validado empíricamente contra la propia base: NO hay arrastre de apertura
    entre ejercicios (saldo_ejercicio_cta = Σ movimientos del ejercicio). Se incluyen
    TODAS las filas (también anulado='Si'), porque cada anulación tiene su contra-
    asiento reversante y ambos se netean. Signo según cont_pc.saldo_pc.
    """
    cur = repo.cur()
    cur.execute("SELECT id_pc, saldo_pc FROM cont_pc")
    natur = {
        int(r["id_pc"]): ((r["saldo_pc"] or "").strip() or "Deudor")
        for r in cur.fetchall()
    }
    cur.execute(
        """SELECT id_pc, id_ejercicio,
                  SUM(COALESCE(debe_asiento,0)) d, SUM(COALESCE(haber_asiento,0)) h
           FROM cont_asiento
           WHERE id_ejercicio IS NOT NULL AND id_pc IS NOT NULL
           GROUP BY id_pc, id_ejercicio"""
    )
    saldos = {}
    for r in cur.fetchall():
        id_pc, id_ej = int(r["id_pc"]), int(r["id_ejercicio"])
        debe, haber = r2(r["d"]), r2(r["h"])
        signo = (haber - debe) if natur.get(id_pc) == "Acreedor" else (debe - haber)
        saldos[(id_pc, id_ej)] = signo.quantize(Q2, rounding=ROUND_HALF_UP)
    return saldos


def rebuild_saldos(commit=True):
    """Reconstruye totalmente cont_ejercicio_saldo_cta desde el diario (fuente de verdad).

    commit=False -> dry-run (solo informa el diff, no escribe).
    """
    conn = MySQLdb.connect(**DB)
    conn.autocommit(False)
    repo = Repo(conn)
    calc = _saldos_derivados(repo)

    cur = repo.cur()
    cur.execute(
        "SELECT id_pc, id_ejercicio, saldo_ejercicio_cta FROM cont_ejercicio_saldo_cta"
    )
    stored = {}
    for r in cur.fetchall():
        stored[(int(r["id_pc"]), int(r["id_ejercicio"]))] = r2(r["saldo_ejercicio_cta"])

    a_actualizar = []   # (id_pc, id_ej, nuevo, anterior)
    a_insertar = []     # (id_pc, id_ej, nuevo)
    a_cerar = []        # (id_pc, id_ej, anterior) existentes sin movimiento
    for clave, nuevo in calc.items():
        ant = stored.get(clave)
        if ant is None:
            a_insertar.append((clave[0], clave[1], nuevo))
        elif ant != nuevo:
            a_actualizar.append((clave[0], clave[1], nuevo, ant))
    for clave, ant in stored.items():
        if clave not in calc and ant != Decimal("0"):
            a_cerar.append((clave[0], clave[1], ant))

    print(f"[rebuild-saldos] {'APLICAR' if commit else 'DRY-RUN'}")
    print(f"  cuentas/ejercicio calculadas: {len(calc)}")
    print(f"  a actualizar: {len(a_actualizar)}")
    print(f"  a insertar:   {len(a_insertar)}")
    print(f"  a poner en 0 (sin movimiento): {len(a_cerar)}")
    for id_pc, id_ej, nuevo, ant in sorted(a_actualizar, key=lambda x: abs(x[2] - x[3]), reverse=True)[:20]:
        print(f"    upd id_pc={id_pc} ej={id_ej}: {ant} -> {nuevo} (Δ={r2(nuevo - ant)})")

    if not commit:
        conn.close()
        return

    wcur = conn.cursor()
    try:
        for id_pc, id_ej, nuevo, _ant in a_actualizar:
            wcur.execute(
                "UPDATE cont_ejercicio_saldo_cta SET saldo_ejercicio_cta=%s WHERE id_pc=%s AND id_ejercicio=%s",
                (str(nuevo), id_pc, id_ej),
            )
        for id_pc, id_ej, nuevo in a_insertar:
            wcur.execute(
                "INSERT INTO cont_ejercicio_saldo_cta (id_pc, id_ejercicio, saldo_ejercicio_cta) VALUES (%s,%s,%s)",
                (id_pc, id_ej, str(nuevo)),
            )
        for id_pc, id_ej, _ant in a_cerar:
            wcur.execute(
                "UPDATE cont_ejercicio_saldo_cta SET saldo_ejercicio_cta=0 WHERE id_pc=%s AND id_ejercicio=%s",
                (id_pc, id_ej),
            )
        conn.commit()
        print("  => aplicado y confirmado.")
    except Exception as exc:  # noqa: BLE001
        conn.rollback()
        print("  => ERROR, rollback:", exc)
    conn.close()


if __name__ == "__main__":
    mode = sys.argv[1] if len(sys.argv) > 1 else "validate-fa"
    if mode == "validate-fa":
        validate(mode)
    elif mode == "validate-op":
        validate_op()
    elif mode == "dryrun-missing":
        dryrun_missing()
    elif mode == "apply-missing":
        apply_missing()
    elif mode == "rebuild-saldos-dry":
        rebuild_saldos(commit=False)
    elif mode == "rebuild-saldos":
        rebuild_saldos(commit=True)
    else:
        print("modo no implementado aun:", mode)
