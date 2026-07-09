"""
Prueba end-to-end MPR con informe de saldos por depósito en cada fase.
Uso: docker exec Synap_app python manage.py e2e_mpr_trazabilidad --base administranet96
"""
from __future__ import annotations

import json
from datetime import date
from decimal import Decimal
from typing import Any, Dict, List, Optional, Tuple

from django.core.management.base import BaseCommand

from core.utils.administranet_types import to_int_or_none
from mpr.db import mysql_cursor
from mpr.services import (
    TIPO_MPR_2DA_SELECCION,
    TIPO_MPR_PRODUCCION,
    TIPO_MPR_SEMI_ELABORADO,
    TIPO_MPR_TERMINADO,
    _nombre_tabla,
    bulk_bom_detalle,
    bulk_id_en_abm,
    confirmar_imputacion_armado,
    ejecutar_lote_armado,
    enviar_a_produccion_lote,
    get_deposito_produccion_mpr,
    lineas_bom_pack_1ra,
    listar_depositos_config,
    listar_demanda_pack_desde_pedidos,
    listar_tablero_por_articulo,
    listar_tablero_armado,
    obtener_operario,
    obtener_turno,
    registrar_parte_produccion,
    transferir_stock_entre_etapas,
    sugerir_imputacion_fifo,
)


def _log_debug(location: str, message: str, data: dict, hypothesis_id: str = "E2E") -> None:
    # #region agent log
    try:
        import time
        payload = {
            "sessionId": "cb9ea5",
            "runId": "e2e-mpr",
            "hypothesisId": hypothesis_id,
            "location": location,
            "message": message,
            "data": data,
            "timestamp": int(time.time() * 1000),
        }
        with open(
            "/app/.cursor/debug-cb9ea5.log", "a", encoding="utf-8"
        ) as fh:
            fh.write(json.dumps(payload, default=str) + "\n")
    except Exception:
        pass
    # #endregion


class Command(BaseCommand):
    help = "E2E MPR: tablero → envío → parte → CC → armado → imputación con saldos por fase"

    def add_arguments(self, parser):
        parser.add_argument("--base", default="administranet96")
        parser.add_argument("--id-comp", type=int, default=1138, help="IDArt componente")
        parser.add_argument("--id-pack", type=int, default=127, help="IDArt pack terminado")
        parser.add_argument("--cant-envio", type=int, default=24, help="Pares a enviar")
        parser.add_argument("--cant-parte", type=int, default=24, help="Pares en parte")
        parser.add_argument("--cant-semi", type=int, default=20, help="Pares a semi en CC")
        parser.add_argument("--cant-2da", type=int, default=4, help="Pares a 2da en CC")
        parser.add_argument("--cant-armado", type=int, default=10, help="Packs a armar (1ra)")
        parser.add_argument("--id-usuario", type=int, default=1)
        parser.add_argument("--id-operario", type=int, default=1)
        parser.add_argument("--id-turno", type=int, default=1)
        parser.add_argument("--dry-run", action="store_true", help="Solo informe inicial, sin mutar")

    def handle(self, *args, **options):
        base = options["base"]
        id_comp = options["id_comp"]
        id_pack = options["id_pack"]
        id_usuario = options["id_usuario"]
        id_operario = options["id_operario"]
        id_turno = options["id_turno"]
        dry = options["dry_run"]

        articulos = self._resolver_articulos(base, id_pack, id_comp)
        pedidos = self._pedidos_pack(base, id_pack)
        informe: Dict[str, Any] = {
            "base": base,
            "articulos": articulos,
            "pedidos_pack": pedidos,
            "fases": [],
        }

        fase0 = self._snapshot("FASE 0 — Estado inicial", base, articulos)
        informe["fases"].append(fase0)
        _log_debug("e2e:fase0", "snapshot inicial", {"fase0": fase0}, "H1")

        if dry:
            self._print_informe(informe)
            return

        cant_env = options["cant_envio"]
        cant_parte = options["cant_parte"]
        cant_semi = options["cant_semi"]
        cant_2da = options["cant_2da"]
        cant_arm = options["cant_armado"]

        # FASE 1: Envío a fabricación
        ok, n, warns, err = enviar_a_produccion_lote(
            base, id_usuario, [(id_comp, Decimal(cant_env))]
        )
        _log_debug("e2e:envio", "enviar_a_produccion_lote", {
            "ok": ok, "n": n, "warns": warns, "err": err, "cant": cant_env
        }, "H2")
        if not ok:
            self.stderr.write(f"Error envío: {err}")
            self._print_informe(informe)
            return
        informe["fases"].append(self._snapshot("FASE 1 — Tras envío a fabricación", base, articulos))

        # FASE 2: Parte de producción
        if not obtener_turno(base, id_turno):
            self.stderr.write(f"Turno {id_turno} no encontrado")
            return
        if not obtener_operario(base, id_operario):
            self.stderr.write(f"Operario {id_operario} no encontrado")
            return
        parte, p_warns = registrar_parte_produccion(
            base,
            date.today(),
            id_turno,
            id_usuario,
            [{"id_articulo": id_comp, "id_operario": id_operario, "cantidad": cant_parte}],
        )
        _log_debug("e2e:parte", "registrar_parte_produccion", {
            "parte_id": getattr(parte, "id_mpr_parte", None),
            "warns": p_warns,
            "cant": cant_parte,
        }, "H3")
        informe["fases"].append(self._snapshot("FASE 2 — Tras parte de producción", base, articulos))

        # FASE 3: Control de calidad
        if cant_semi > 0:
            ok_s, cod_s, _, err_s = transferir_stock_entre_etapas(
                base, id_usuario, id_comp,
                TIPO_MPR_PRODUCCION, TIPO_MPR_SEMI_ELABORADO,
                cant_semi, id_operario=id_operario,
            )
            _log_debug("e2e:cc_semi", "transferir semi", {"ok": ok_s, "cod": cod_s, "err": err_s}, "H4")
            if not ok_s:
                self.stderr.write(f"Error CC semi: {err_s}")
        if cant_2da > 0:
            ok_2, cod_2, _, err_2 = transferir_stock_entre_etapas(
                base, id_usuario, id_comp,
                TIPO_MPR_PRODUCCION, TIPO_MPR_2DA_SELECCION,
                cant_2da, id_operario=id_operario,
            )
            _log_debug("e2e:cc_2da", "transferir 2da", {"ok": ok_2, "cod": cod_2, "err": err_2}, "H4")
            if not ok_2:
                self.stderr.write(f"Error CC 2da: {err_2}")
        informe["fases"].append(self._snapshot("FASE 3 — Tras control de calidad", base, articulos))

        # FASE 4: Armado 1ra
        deps = {d["tipo_mpr"]: d["CodDeposito"] for d in listar_depositos_config(base) if d.get("tipo_mpr")}
        dep_semi = deps.get(TIPO_MPR_SEMI_ELABORADO)
        dep_term = deps.get(TIPO_MPR_TERMINADO)
        bom_lineas = lineas_bom_pack_1ra(base, id_pack)
        item_armado = {
            "id_articulo_pack": id_pack,
            "cantidad_packs": cant_arm,
            "lineas": [
                {
                    "id_articulo": int(ln["id_articulo"]),
                    "cantidad_por_pack": int(ln["cantidad_por_pack"]),
                }
                for ln in bom_lineas
            ],
        }
        resultado_arm = ejecutar_lote_armado(
            base,
            id_usuario,
            {
                "modo": "1ra",
                "deposito_origen": dep_semi,
                "deposito_destino": dep_term,
                "id_operario": id_operario,
            },
            [item_armado],
        )
        cod_mstock = None
        if resultado_arm.get("exitosos"):
            cod_mstock = resultado_arm["exitosos"][0].get("codigo_movimiento")
        _log_debug("e2e:armado", "ejecutar_lote_armado", {
            "exitosos": len(resultado_arm.get("exitosos", [])),
            "fallidos": resultado_arm.get("fallidos"),
            "cod_mstock": cod_mstock,
        }, "H5")
        informe["fases"].append(self._snapshot("FASE 4 — Tras armado", base, articulos))

        # FASE 5: Imputación a pedido
        if cod_mstock:
            lineas_imp, err_fifo = sugerir_imputacion_fifo(base, int(cod_mstock))
            if lineas_imp:
                ok_i, err_i = confirmar_imputacion_armado(
                    base, int(cod_mstock), lineas_imp, id_usuario
                )
                _log_debug("e2e:imputacion", "confirmar_imputacion", {
                    "ok": ok_i, "err": err_i, "lineas": lineas_imp,
                }, "H6")
            else:
                _log_debug("e2e:imputacion", "sin lineas fifo", {
                    "err_fifo": err_fifo, "cod_mstock": cod_mstock,
                }, "H6")
        informe["fases"].append(self._snapshot("FASE 5 — Tras imputación a pedido", base, articulos))

        self._print_informe(informe)

    def _resolver_articulos(self, base: str, id_pack: int, id_comp: int) -> Dict[str, Any]:
        ids = [id_pack, id_comp]
        bom_lineas = lineas_bom_pack_1ra(base, id_pack)
        comp_ids = [l["id_articulo"] for l in bom_lineas]
        ids = sorted(set(ids + comp_ids))
        nombres = {}
        with mysql_cursor(base, dict_cursor=True) as cur:
            tbl = _nombre_tabla(cur, "articulo")
            placeholders = ",".join(["%s"] * len(ids))
            cur.execute(
                f"SELECT IDArt, CodigoArticuloT, NombreArticulo, tipo_art_fab FROM {tbl} WHERE IDArt IN ({placeholders})",
                ids,
            )
            for r in cur.fetchall() or []:
                nombres[r["IDArt"]] = r
        tab = {t["id_articulo"]: t for t in listar_tablero_por_articulo(base, limit=500)}
        dem_pack = next((d for d in listar_demanda_pack_desde_pedidos(base) if d.get("id_articulo") == id_pack), {})
        return {
            "pack": {"id": id_pack, **(nombres.get(id_pack) or {})},
            "componente_principal": {"id": id_comp, **(nombres.get(id_comp) or {})},
            "bom": bom_lineas,
            "tablero_componente": tab.get(id_comp, {}),
            "demanda_pack": dem_pack,
        }

    def _pedidos_pack(self, base: str, id_pack: int) -> List[Dict[str, Any]]:
        with mysql_cursor(base, dict_cursor=True) as cur:
            tbl_sp = _nombre_tabla(cur, "stockp")
            tbl_cp = _nombre_tabla(cur, "comp_ped")
            cur.execute(
                f"""
                SELECT cp.CodigoMovimiento, cp.NroComprobante, cp.Fecha, cp.FechaEntrega,
                       cp.estado_pedido_opt, sp.Cantidad, sp.cantidad_entregada, sp.cantidad_pendiente
                FROM {tbl_sp} sp
                INNER JOIN {tbl_cp} cp ON cp.CodigoMovimiento = sp.CodigoMovimiento
                WHERE sp.IDArt = %s AND cp.TipoComprobante = 'PED' AND cp.Anulado = 'No'
                ORDER BY cp.Fecha ASC
                """,
                [id_pack],
            )
            return list(cur.fetchall() or [])

    def _snapshot(self, nombre: str, base: str, articulos: Dict[str, Any]) -> Dict[str, Any]:
        ids = [articulos["pack"]["id"], articulos["componente_principal"]["id"]]
        for b in articulos.get("bom") or []:
            ids.append(b["id_articulo"])
        ids = sorted(set(ids))
        saldos = {str(aid): self._saldos_articulo(base, aid) for aid in ids}
        return {"nombre": nombre, "saldos": saldos}

    def _saldos_articulo(self, base: str, id_articulo: int) -> Dict[str, Any]:
        filas = []
        pivot_mpr = {}
        with mysql_cursor(base, dict_cursor=True) as cur:
            tbl_sd = _nombre_tabla(cur, "stock_deposito")
            tbl_dep = _nombre_tabla(cur, "deposito")
            cur.execute(
                f"""
                SELECT d.CodDeposito, d.NombreDeposito, COALESCE(d.tipo_mpr,'') AS tipo_mpr,
                       COALESCE(d.suma_stock,'Si') AS suma_stock,
                       COALESCE(sd.saldo,0) AS saldo
                FROM {tbl_dep} d
                LEFT JOIN {tbl_sd} sd ON sd.id_deposito = d.CodDeposito AND sd.id_articulo = %s
                WHERE COALESCE(d.anulado,'No') = 'No'
                ORDER BY d.NombreDeposito
                """,
                [id_articulo],
            )
            for r in cur.fetchall() or []:
                saldo = float(r.get("saldo") or 0)
                tipo = (r.get("tipo_mpr") or "").strip()
                if tipo:
                    pivot_mpr[tipo] = pivot_mpr.get(tipo, 0.0) + saldo
                filas.append({
                    "deposito": r.get("CodDeposito"),
                    "nombre": r.get("NombreDeposito"),
                    "tipo_mpr": tipo or None,
                    "suma_stock": r.get("suma_stock"),
                    "saldo": saldo,
                })
        return {"id_articulo": id_articulo, "depositos": filas, "pivot_mpr": pivot_mpr}

    def _print_informe(self, informe: Dict[str, Any]) -> None:
        self.stdout.write("\n" + "=" * 80)
        self.stdout.write("INFORME E2E MPR — TRAZABILIDAD DE SALDOS")
        self.stdout.write("=" * 80)
        arts = informe["articulos"]
        pack = arts["pack"]
        comp = arts["componente_principal"]
        self.stdout.write(f"\nBase: {informe['base']}")
        self.stdout.write(f"Pack: IDArt {pack['id']} — {pack.get('NombreArticulo','')}")
        self.stdout.write(f"Componente: IDArt {comp['id']} — {comp.get('NombreArticulo','')}")
        self.stdout.write("\n--- PEDIDOS (pack) ---")
        for p in informe.get("pedidos_pack") or []:
            self.stdout.write(
                f"  PED {p.get('NroComprobante')} cod_mov={p.get('CodigoMovimiento')} "
                f"fecha={p.get('Fecha')} cant={p.get('Cantidad')} pend={p.get('cantidad_pendiente')} "
                f"estado={p.get('estado_pedido_opt')}"
            )
        dem = arts.get("demanda_pack") or {}
        self.stdout.write(
            f"\nDemanda pack agregada: pedido={dem.get('cantidad_pedida_pedido')} "
            f"reserva={dem.get('cantidad_demanda_reserva')} stock_terminado={dem.get('stock_terminado')} "
            f"a_fabricar={dem.get('cantidad_a_fabricar')}"
        )
        tab = arts.get("tablero_componente") or {}
        self.stdout.write(
            f"Tablero componente: dem_ped={tab.get('dem_ped')} enviado={tab.get('enviado')} "
            f"produccion={tab.get('produccion')} semi={tab.get('semi_elaborado')} "
            f"2da={tab.get('segunda_seleccion')} resta_urgente={tab.get('resta_urgente')}"
        )
        for fase in informe.get("fases") or []:
            self.stdout.write(f"\n{'—' * 60}")
            self.stdout.write(fase["nombre"])
            self.stdout.write(f"{'—' * 60}")
            for aid, data in (fase.get("saldos") or {}).items():
                self.stdout.write(f"\n  Artículo {aid} — pivot MPR: {data.get('pivot_mpr')}")
                for dep in data.get("depositos") or []:
                    if dep["saldo"] != 0 or dep.get("tipo_mpr"):
                        self.stdout.write(
                            f"    Dep {dep['deposito']:>3} {dep['nombre'][:28]:28} "
                            f"tipo={dep.get('tipo_mpr') or '-':15} saldo={dep['saldo']:>10.0f}"
                        )
        self.stdout.write("\n" + "=" * 80 + "\n")
