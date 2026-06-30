# MPR — Auditoría de trazabilidad OPT (agrupada + OPP + OPA + coherencia UI).
# Uso: docker exec Synap_app python manage.py auditar_opt_trazabilidad 2 5 7 8 11 --base-empresa=administranet96
# Sin ids: audita las 20 OPT liberadas más recientes.

from django.core.management.base import BaseCommand

from core.mysql_pool import mysql_cursor
from core.utils.administranet_types import to_int_or_none
from mpr.services import (
    _mpr_es_codigo_movimiento_opt_mstock,
    _nombre_tabla,
    bulk_id_en_abm,
    bulk_restante_armar_opt_listado,
    calcular_porcentaje_progreso_opt,
    get_cantidad_opp_por_destino_opt,
    get_cantidades_armadas_por_opt,
    get_deposito_semi_elaborado_mpr,
    get_op_detalle,
    listar_opa_por_opt,
    listar_opp_por_opt,
    listar_opt_listado,
)


def _codigo_movimiento_opt_agrupada(base: str, id_lista: int):
    """codigo_movimiento_opt no viene en get_op_detalle; leer directo de agrupada."""
    try:
        with mysql_cursor(base, dict_cursor=True) as cursor:
            tbl = _nombre_tabla(cursor, "lista_produccion_agrupada")
            if not tbl:
                return None
            cursor.execute(
                f"SELECT codigo_movimiento_opt FROM {tbl} WHERE id_lista_produccion = %s LIMIT 1",
                [id_lista],
            )
            row = cursor.fetchone()
            return to_int_or_none((row or {}).get("codigo_movimiento_opt"))
    except Exception:
        return None


class Command(BaseCommand):
    help = (
        "Audita OPTs por trazabilidad: lista_produccion_agrupada, movimientos OPP/OPA "
        "y coherencia con métricas del listado Synap."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "id_listas",
            nargs="*",
            type=int,
            help="id_lista_produccion a auditar (vacío = últimas 20 OPT liberadas).",
        )
        parser.add_argument(
            "--base-empresa",
            type=str,
            required=True,
            help="Base MySQL AdministraNET (ej. administranet96).",
        )

    def handle(self, *args, **options):
        base = (options.get("base_empresa") or "").strip()
        if not base:
            self.stdout.write(self.style.ERROR("Indique --base-empresa."))
            return

        ids = list(options.get("id_listas") or [])
        if not ids:
            filas = listar_opt_listado(base, limit=20)
            ids = sorted(
                {
                    int(f["id_lista_produccion"])
                    for f in filas
                    if f.get("id_lista_produccion")
                },
                reverse=True,
            )

        if not ids:
            self.stdout.write(self.style.WARNING("No hay OPTs para auditar."))
            return

        alertas_globales = 0
        for id_lista in ids:
            alertas_globales += self._auditar_una(base, int(id_lista))

        self.stdout.write("")
        if alertas_globales:
            self.stdout.write(
                self.style.WARNING(
                    f"Total alertas de coherencia: {alertas_globales} "
                    f"(revise líneas marcadas con ⚠)."
                )
            )
        else:
            self.stdout.write(self.style.SUCCESS("Sin alertas de coherencia en el lote auditado."))

    def _auditar_una(self, base: str, id_lista: int) -> int:
        alertas = 0
        self.stdout.write("")
        self.stdout.write(self.style.HTTP_INFO(f"{'=' * 72}"))
        self.stdout.write(self.style.HTTP_INFO(f"OPT id_lista_produccion = {id_lista}"))
        self.stdout.write(self.style.HTTP_INFO(f"{'=' * 72}"))

        lineas = get_op_detalle(base, id_lista)
        if not lineas:
            self.stdout.write(self.style.ERROR("  ⚠ Sin fila en lista_produccion_agrupada."))
            return 1

        l = lineas[0]
        id_art = to_int_or_none(l.get("id_articulo"))
        pedida = int(l.get("cantidad_pedida") or 0)
        pend_opp = int(l.get("cantidad_pendiente_prod") or 0)
        asignada = l.get("cantidad_asignada_opt")
        asignada_int = int(asignada) if asignada is not None else None
        en_proc = (l.get("en_proceso_produccion") or "No").strip()
        en_proc_si = en_proc == "Si"
        cod_opt = _codigo_movimiento_opt_agrupada(base, id_lista)

        if asignada_int is not None and asignada_int > 0:
            pend_pedido_ui = max(0, pedida - asignada_int)
        else:
            pend_pedido_ui = pend_opp

        pct_ui = calcular_porcentaje_progreso_opt(en_proc_si, pend_opp)

        self.stdout.write(
            f"  Artículo: {l.get('codigo_articulo')} (id={id_art}) — {str(l.get('descripcion_articulo') or '')[:50]}"
        )
        self.stdout.write(
            f"  agrupada: pedida={pedida} pend_OPP={pend_opp} asignada_opt={asignada} "
            f"en_proceso={en_proc} cod_mov_OPT={cod_opt}"
        )
        self.stdout.write(f"  UI listado: pend_pedido≈{pend_pedido_ui} progreso%={pct_ui}")

        # Trazabilidad movimientos
        opps = listar_opp_por_opt(base, id_lista)
        opas = listar_opa_por_opt(base, id_lista)
        semi, otros, desp = get_cantidad_opp_por_destino_opt(base, id_lista)
        armadas = get_cantidades_armadas_por_opt(base, id_lista)
        abm = bulk_id_en_abm(base, [id_art]) if id_art else {}
        rest_map = bulk_restante_armar_opt_listado(
            base,
            [{
                "id_lista_produccion": id_lista,
                "id_articulo": id_art,
                "cantidad_pendiente_prod": pend_opp,
            }],
            abm,
        )
        rest_armar = int(rest_map.get(f"{id_lista}:{id_art}", 0) or 0)

        dep_semi = get_deposito_semi_elaborado_mpr(base)
        self.stdout.write(f"  Depósito Semi elaborado MPR: {dep_semi}")

        self.stdout.write(f"  Trazabilidad: OPP={len(opps)} mov(s) | OPA/Armado={len(opas)} mov(s)")
        for o in opps[:5]:
            self.stdout.write(
                f"    OPP cod={o.get('codigo_movimiento')} comp={o.get('nro_comprobante')} "
                f"dep_dest={o.get('deposito_destino')} ({o.get('nombre_destino')}) "
                f"cant={o.get('cantidad_total')}"
            )
        if len(opps) > 5:
            self.stdout.write(f"    … (+{len(opps) - 5} OPP)")
        for o in opas[:5]:
            self.stdout.write(
                f"    OPA cod={o.get('codigo_movimiento')} comp={o.get('nro_comprobante')} "
                f"det={str(o.get('detalle') or '')[:55]}"
            )
        if len(opas) > 5:
            self.stdout.write(f"    … (+{len(opas) - 5} OPA)")

        self.stdout.write(f"  OPP→Semi (componentes, unid.): {semi}")
        self.stdout.write(f"  Ya armado (packs Entrada stock): {armadas}")
        self.stdout.write(f"  Restante armar (semi→pack, UI): {rest_armar}")

        # Reglas de coherencia
        checks = []

        if pedida == 0 and pend_opp == 0:
            checks.append(("pedida_cero", "cantidad_pedida=0 (fila huérfana o dato incompleto)"))

        if pend_opp > pedida and pedida > 0:
            checks.append((
                "pend_mayor_pedida",
                f"pend_OPP ({pend_opp}) > cantidad_pedida ({pedida}) — OPP no descontó bien o pedida desactualizada",
            ))

        if not en_proc_si and pend_opp > 0:
            checks.append((
                "cerrada_con_pend_opp",
                f"en_proceso=No pero pend_OPP={pend_opp} — OPT «cerrada» con producción pendiente (estado inconsistente)",
            ))

        if not en_proc_si and pend_opp == 0 and pct_ui == 100:
            pass  # esperado: cerrada y OPP completa
        elif not en_proc_si and pend_opp > 0 and pct_ui == 100:
            checks.append((
                "progreso_100_con_pend",
                f"progreso UI=100% pero pend_OPP={pend_opp} — el % ignora pendiente si en_proceso=No",
            ))

        if asignada_int is not None and asignada_int > pedida:
            checks.append((
                "asignada_mayor_pedida",
                f"cantidad_asignada_opt ({asignada_int}) > cantidad_pedida ({pedida})",
            ))

        if pend_opp == 0 and rest_armar > 0 and not abm.get(id_art):
            checks.append((
                "armado_sin_bom",
                f"restante_armar={rest_armar} pero artículo sin BOM/ensamblado en abm_map",
            ))

        if pend_opp == 0 and rest_armar > 0:
            checks.append((
                "armado_pendiente_ok",
                f"OPP=0 y restante_armar={rest_armar} — badge «Armado pend.» esperado (semi sin armar)",
            ))

        if pend_opp == 0 and rest_armar == 0 and len(opas) == 0 and abm.get(id_art):
            checks.append((
                "bom_sin_armado",
                "Pack armable (BOM) pero sin movimientos OPA vinculados a esta OPT",
            ))

        if len(opps) == 0 and pend_opp < pedida and en_proc_si:
            checks.append((
                "sin_opp_en_proceso",
                "OPT en proceso sin ningún movimiento OPP registrado",
            ))

        if len(opps) > 0 and not semi and dep_semi is not None:
            destinos = {o.get("deposito_destino") for o in opps}
            if dep_semi not in destinos:
                checks.append((
                    "opp_sin_entrada_semi",
                    f"Hay {len(opps)} OPP pero semi vacío — destino OPP {destinos} ≠ Semi MPR ({dep_semi})",
                ))

        cod_int = to_int_or_none(cod_opt)
        if cod_int is None or cod_int <= 0:
            checks.append((
                "sin_cod_mov_opt",
                "codigo_movimiento_opt ausente o placeholder — OPT no liberada correctamente",
            ))
        elif not _mpr_es_codigo_movimiento_opt_mstock(cod_int):
            checks.append((
                "cod_mov_opt_invalido",
                f"codigo_movimiento_opt={cod_int} no es MSTOCK OPT válido (¿placeholder negativo?)",
            ))

        for cod, msg in checks:
            if cod in ("armado_pendiente_ok",):
                self.stdout.write(self.style.SUCCESS(f"  ✓ {msg}"))
            else:
                self.stdout.write(self.style.WARNING(f"  ⚠ {msg}"))
                alertas += 1

        if not checks:
            self.stdout.write(self.style.SUCCESS("  ✓ Sin alertas en reglas básicas."))

        return alertas
