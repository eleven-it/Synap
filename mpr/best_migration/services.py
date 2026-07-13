"""Servicios de paridad y persistencia del mapeo BEST."""

from __future__ import annotations

import logging
from collections import Counter
from typing import Any

from django.db import transaction
from django.utils import timezone

from mpr.best_migration.article_matcher import match_open_order_skus
from mpr.best_migration.client_matcher import match_clients
from mpr.best_migration.connection import connect_best, fetch_dict
from mpr.best_migration.dictionary import DICT_VERSION
from mpr.best_migration.domains import DOMAINS, domains_required_for_orders
from mpr.best_migration.deposit_matcher import BEST_DEPOSITO_TIPO_MPR, match_depositos, norm_text
from mpr.best_migration.models import (
    BestArticuloMap,
    BestClienteMap,
    BestDepositoMap,
    BestMigrationParity,
    BestStockInicialMap,
)
from mpr.services import actualizar_deposito_tipo_mpr, listar_depositos_config
from core.utils.administranet_types import str_or_default, to_decimal_or_none, to_int_or_none
from mpr.db import mysql_cursor

logger = logging.getLogger(__name__)

ESTADOS_PENDIENTES_ARTICULO = {
    BestArticuloMap.Estado.INFERIDO_ALTO,
    BestArticuloMap.Estado.INFERIDO_MEDIO,
    BestArticuloMap.Estado.INFERIDO_BAJO,
    BestArticuloMap.Estado.AMBIGUO,
    BestArticuloMap.Estado.SIN_CANDIDATO,
    BestArticuloMap.Estado.SIN_MATCH,
    BestArticuloMap.Estado.CONFLICTO_1_A_N,
}

_FLAGS_ALCANCE_ABIERTO = {
    "requerido_migracion": True,
    "en_snapshot_abierto": True,
    "origen_requerimiento": BestArticuloMap.OrigenRequerimiento.PEDIDO_ABIERTO,
}

_FLAGS_ALCANCE_HISTORICO_ART = {
    "requerido_migracion": False,
    "en_snapshot_abierto": False,
    "origen_requerimiento": BestArticuloMap.OrigenRequerimiento.HISTORICO,
}

_FLAGS_ALCANCE_HISTORICO_DEP = {
    "requerido_migracion": False,
    "en_snapshot_abierto": False,
    "origen_requerimiento": BestDepositoMap.OrigenRequerimiento.HISTORICO,
}

_FLAGS_ALCANCE_HISTORICO_CLI = {
    "requerido_migracion": False,
    "en_snapshot_abierto": False,
    "origen_requerimiento": BestClienteMap.OrigenRequerimiento.HISTORICO,
}

_FLAGS_ALCANCE_STOCK_DEP = {
    "requerido_migracion": True,
    "en_snapshot_abierto": True,
    "origen_requerimiento": BestDepositoMap.OrigenRequerimiento.STOCK_DEPOSITO,
}

_FLAGS_ALCANCE_PEDIDO_DEP = {
    "requerido_migracion": True,
    "en_snapshot_abierto": True,
    "origen_requerimiento": BestDepositoMap.OrigenRequerimiento.PEDIDO_ABIERTO,
}


def _conteo_categorias_migracion(qs) -> dict[str, int]:
    """Agrega contadores de categoría sobre un queryset de mapeo."""
    cumplen = necesarios_pendientes = no_necesarios = excluidos = 0
    cumplen_stock = necesarios_stock = 0
    for obj in qs:
        cat = obj.categoria_migracion
        if cat == "CUMPLE":
            cumplen += 1
        elif cat == "CUMPLE_STOCK":
            cumplen_stock += 1
        elif cat == "NECESARIO_PENDIENTE":
            necesarios_pendientes += 1
        elif cat == "NECESARIO_STOCK":
            necesarios_stock += 1
        elif cat == "NO_NECESARIO":
            no_necesarios += 1
        elif cat == "EXCLUIDO":
            excluidos += 1
    requeridos = qs.filter(requerido_migracion=True)
    requeridos_total = requeridos.count()
    requeridos_resueltos = sum(1 for o in requeridos if o.resuelto_para_migracion)
    return {
        "requeridos_total": requeridos_total,
        "requeridos_resueltos": requeridos_resueltos,
        "requeridos_pendientes": requeridos_total - requeridos_resueltos,
        "cumplen": cumplen,
        "cumplen_stock": cumplen_stock,
        "necesarios_pendientes": necesarios_pendientes,
        "necesarios_stock": necesarios_stock,
        "no_necesarios": no_necesarios,
        "excluidos": excluidos,
        "fuera_alcance": no_necesarios,
    }


def _load_admin_articulos(base_empresa: str) -> list[dict]:
    with mysql_cursor(base_empresa, dict_cursor=True) as cur:
        cur.execute(
            """
            SELECT IDArt,
                   TRIM(COALESCE(id_manual, '')) AS id_manual,
                   TRIM(COALESCE(NombreArticulo, '')) AS NombreArticulo,
                   TRIM(COALESCE(CodArtProv, '')) AS CodArtProv
            FROM articulo
            """
        )
        return list(cur.fetchall())


def _fetch_best_open_skus() -> tuple[list[dict], dict[str, dict]]:
    conn = connect_best()
    try:
        best_rows = fetch_dict(
            conn,
            """
            SELECT DISTINCT
                c.[Id Articulo] AS id_articulo,
                c.Codigo AS codigo,
                c.Articulo AS articulo,
                c.Marca AS marca
            FROM REP_ORDENES_COMBINADO c
            WHERE c.Finalizada = 0 AND c.Pendiente > 0
            """,
        )
        myl_rows = fetch_dict(
            conn,
            """
            SELECT MYMMID, CODIGO, COLOR, COLOR1, COLOR2, COLOR3, TALLE, PACK, MARCADS
            FROM MYL
            WHERE MYMMID IN (
                SELECT DISTINCT [Id Articulo]
                FROM REP_ORDENES_COMBINADO
                WHERE Finalizada = 0 AND Pendiente > 0
            )
            """,
        )
        myl = {str(r["MYMMID"]): r for r in myl_rows}
        return best_rows, myl
    finally:
        conn.close()


def _fetch_best_inventory_skus() -> tuple[list[dict], dict[str, dict]]:
    conn = connect_best()
    try:
        best_rows = fetch_dict(
            conn,
            """
            SELECT DISTINCT
                [Id Articulo] AS id_articulo,
                Codigo AS codigo,
                Articulo AS articulo,
                Marca AS marca
            FROM REP_INVENTARIOS
            WHERE COALESCE(Stock, 0) <> 0
            """,
        )
        myl_rows = fetch_dict(
            conn,
            """
            SELECT MYMMID, CODIGO, COLOR, COLOR1, COLOR2, COLOR3, TALLE, PACK, MARCADS
            FROM MYL
            WHERE MYMMID IN (
                SELECT DISTINCT [Id Articulo]
                FROM REP_INVENTARIOS
                WHERE COALESCE(Stock, 0) <> 0
            )
            """,
        )
        myl = {str(r["MYMMID"]): r for r in myl_rows}
        return best_rows, myl
    finally:
        conn.close()


def _fetch_best_open_clients() -> list[dict]:
    conn = connect_best()
    try:
        return fetch_dict(
            conn,
            """
            SELECT
                Cliente AS best_cliente,
                CUIT AS best_cuit,
                COUNT(DISTINCT [Orden Nro]) AS ordenes_abiertas
            FROM REP_ORDENES_COMBINADO
            WHERE Finalizada = 0 AND Pendiente > 0
            GROUP BY Cliente, CUIT
            """,
        )
    finally:
        conn.close()


@transaction.atomic
def asegurar_articulos_desde_inventario(base_empresa: str) -> dict[str, Any]:
    """Asegura BestArticuloMap para SKUs con saldo en REP_INVENTARIOS (Stock ≠ 0)."""
    best_rows, myl = _fetch_best_inventory_skus()
    admin_arts = _load_admin_articulos(base_empresa)
    matches = match_open_order_skus(
        best_rows=best_rows, myl_by_mmid=myl, admin_arts=admin_arts
    )

    preservados = {
        m.best_id_articulo: m
        for m in BestArticuloMap.objects.filter(
            base_empresa=base_empresa,
            estado__in=[
                BestArticuloMap.Estado.VALIDADO,
                BestArticuloMap.Estado.DESCARTADO,
            ],
        )
    }

    created = updated = preserved = 0
    for row in matches:
        prev = preservados.get(row.best_id_articulo)
        defaults_meta = {
            "best_codigo": row.best_codigo,
            "best_articulo": row.best_articulo[:255],
            "best_marca": row.best_marca[:64],
            "best_modelos": row.best_modelos[:128],
            "best_colores": row.best_colores[:64],
            "best_color_mode": row.best_color_mode[:16],
            "best_talle": row.best_talle[:8],
            "best_pack": row.best_pack[:8],
            "best_variant_codes": row.best_variant_codes[:128],
            "dict_version": DICT_VERSION,
            "candidatos_n": row.candidatos_n,
            "alt1_idart": row.alt1_idart,
            "alt1_nombre": (row.alt1_nombre or "")[:255],
            "alt1_score": row.alt1_score,
            "alt2_idart": row.alt2_idart,
            "alt2_nombre": (row.alt2_nombre or "")[:255],
            "alt2_score": row.alt2_score,
        }

        if prev:
            for k, v in defaults_meta.items():
                setattr(prev, k, v)
            prev.requerido_migracion = True
            prev.en_snapshot_abierto = True
            prev.save()
            preserved += 1
            continue

        existing = BestArticuloMap.objects.filter(
            base_empresa=base_empresa,
            best_id_articulo=row.best_id_articulo,
        ).first()
        origen = (
            BestArticuloMap.OrigenRequerimiento.PEDIDO_ABIERTO
            if existing
            and existing.origen_requerimiento
            == BestArticuloMap.OrigenRequerimiento.PEDIDO_ABIERTO
            else BestArticuloMap.OrigenRequerimiento.STOCK_DEPOSITO
        )

        obj, was_created = BestArticuloMap.objects.update_or_create(
            base_empresa=base_empresa,
            best_id_articulo=row.best_id_articulo,
            defaults={
                **defaults_meta,
                "admin_idart": row.admin_idart,
                "admin_id_manual": (row.admin_id_manual or "")[:64],
                "admin_nombre": (row.admin_nombre or "")[:255],
                "admin_cod_art_prov": (row.admin_cod_art_prov or "")[:128],
                "admin_pack": (row.admin_pack or "")[:8],
                "admin_talle": (row.admin_talle or "")[:8],
                "admin_color_mode": (row.admin_color_mode or "")[:16],
                "estado": row.status,
                "score": row.score,
                "razon": (row.razon or "")[:512],
                "requerido_migracion": True,
                "en_snapshot_abierto": True,
                "origen_requerimiento": origen,
                "validado": False,
                "validado_por": "",
                "validado_en": None,
            },
        )
        if was_created:
            created += 1
        else:
            updated += 1

    refresh_parity_counters(base_empresa).save()
    return {
        "created": created,
        "updated": updated,
        "preserved": preserved,
        "total": len(matches),
    }


@transaction.atomic
def recalcular_mapeo_articulos(base_empresa: str) -> dict[str, Any]:
    """Recalcula inferencias desde BEST + Admin. Preserva VALIDADO/DESCARTADO manuales."""
    best_rows, myl = _fetch_best_open_skus()
    admin_arts = _load_admin_articulos(base_empresa)
    matches = match_open_order_skus(
        best_rows=best_rows, myl_by_mmid=myl, admin_arts=admin_arts
    )

    preservados = {
        m.best_id_articulo: m
        for m in BestArticuloMap.objects.filter(
            base_empresa=base_empresa,
            estado__in=[
                BestArticuloMap.Estado.VALIDADO,
                BestArticuloMap.Estado.DESCARTADO,
            ],
        )
    }

    vistos: set[str] = set()
    created = updated = preserved = 0
    for row in matches:
        vistos.add(row.best_id_articulo)
        prev = preservados.get(row.best_id_articulo)
        defaults = {
            "best_codigo": row.best_codigo,
            "best_articulo": row.best_articulo[:255],
            "best_marca": row.best_marca[:64],
            "best_modelos": row.best_modelos[:128],
            "best_colores": row.best_colores[:64],
            "best_color_mode": row.best_color_mode[:16],
            "best_talle": row.best_talle[:8],
            "best_pack": row.best_pack[:8],
            "best_variant_codes": row.best_variant_codes[:128],
            "dict_version": DICT_VERSION,
            "candidatos_n": row.candidatos_n,
            "alt1_idart": row.alt1_idart,
            "alt1_nombre": (row.alt1_nombre or "")[:255],
            "alt1_score": row.alt1_score,
            "alt2_idart": row.alt2_idart,
            "alt2_nombre": (row.alt2_nombre or "")[:255],
            "alt2_score": row.alt2_score,
            **_FLAGS_ALCANCE_ABIERTO,
        }
        if prev:
            # Solo refresca metadatos BEST; no pisa validación humana
            for k, v in defaults.items():
                setattr(prev, k, v)
            prev.save()
            preserved += 1
            continue

        obj, was_created = BestArticuloMap.objects.update_or_create(
            base_empresa=base_empresa,
            best_id_articulo=row.best_id_articulo,
            defaults={
                **defaults,
                "admin_idart": row.admin_idart,
                "admin_id_manual": (row.admin_id_manual or "")[:64],
                "admin_nombre": (row.admin_nombre or "")[:255],
                "admin_cod_art_prov": (row.admin_cod_art_prov or "")[:128],
                "admin_pack": (row.admin_pack or "")[:8],
                "admin_talle": (row.admin_talle or "")[:8],
                "admin_color_mode": (row.admin_color_mode or "")[:16],
                "estado": row.status,
                "score": row.score,
                "razon": (row.razon or "")[:512],
                "validado": False,
                "validado_por": "",
                "validado_en": None,
            },
        )
        if was_created:
            created += 1
        else:
            updated += 1

    # Validados/descartados fuera del snapshot abierto → histórico (no borrar)
    for best_id, prev in preservados.items():
        if best_id not in vistos:
            for k, v in _FLAGS_ALCANCE_HISTORICO_ART.items():
                setattr(prev, k, v)
            prev.save(
                update_fields=[
                    "requerido_migracion",
                    "en_snapshot_abierto",
                    "origen_requerimiento",
                    "actualizado_en",
                ]
            )

    # Quitar SKUs que ya no están en pedidos abiertos (salvo validados/descartados e inventario)
    BestArticuloMap.objects.filter(base_empresa=base_empresa).exclude(
        best_id_articulo__in=vistos
    ).exclude(
        estado__in=[BestArticuloMap.Estado.VALIDADO, BestArticuloMap.Estado.DESCARTADO]
    ).exclude(
        origen_requerimiento=BestArticuloMap.OrigenRequerimiento.STOCK_DEPOSITO,
        requerido_migracion=True,
    ).delete()

    asegurar_articulos_desde_inventario(base_empresa)

    parity = refresh_parity_counters(base_empresa)
    parity.ultimo_recalculo_articulos = timezone.now()
    parity.ultimo_error = ""
    parity.save(
        update_fields=[
            "articulos_total",
            "articulos_resueltos",
            "articulos_ok",
            "clientes_total",
            "clientes_resueltos",
            "clientes_ok",
            "migracion_habilitada",
            "ultimo_recalculo_articulos",
            "ultimo_error",
            "actualizado_en",
        ]
    )
    return {
        "created": created,
        "updated": updated,
        "preserved": preserved,
        "total": len(matches),
        "dict_version": DICT_VERSION,
        "parity": parity,
    }


def _load_admin_clientes(base_empresa: str) -> list[dict]:
    with mysql_cursor(base_empresa, dict_cursor=True) as cur:
        cur.execute(
            """
            SELECT Codigo,
                   TRIM(COALESCE(nombre_cliente, '')) AS nombre_cliente,
                   TRIM(COALESCE(CUIT, '')) AS CUIT,
                   TRIM(COALESCE(id_manual_cli, '')) AS id_manual_cli,
                   TRIM(COALESCE(nombre_fantasia, '')) AS nombre_fantasia
            FROM cliente
            """
        )
        return list(cur.fetchall())


@transaction.atomic
def sincronizar_clientes_abiertos(base_empresa: str) -> dict[str, Any]:
    """Sincroniza clientes de pedidos abiertos BEST e infiere mapeo 1:1."""
    rows = _fetch_best_open_clients()
    admin_clients = _load_admin_clientes(base_empresa)
    matches = match_clients(best_rows=rows, admin_clients=admin_clients)

    preservados = {
        (m.best_cliente, m.best_cuit): m
        for m in BestClienteMap.objects.filter(
            base_empresa=base_empresa,
            estado__in=[BestClienteMap.Estado.VALIDADO, BestClienteMap.Estado.DESCARTADO],
        )
    }

    created = updated = preserved = 0
    vistos: set[tuple[str, str]] = set()
    for row in matches:
        key = (row.best_cliente[:255], (row.best_cuit or "")[:32])
        vistos.add(key)
        prev = preservados.get(key)
        if prev:
            prev.ordenes_abiertas = row.ordenes_abiertas
            for k, v in _FLAGS_ALCANCE_ABIERTO.items():
                setattr(prev, k, v)
            prev.save(
                update_fields=[
                    "ordenes_abiertas",
                    "requerido_migracion",
                    "en_snapshot_abierto",
                    "origen_requerimiento",
                    "actualizado_en",
                ]
            )
            preserved += 1
            continue

        estado = {
            "INFERIDO": BestClienteMap.Estado.INFERIDO,
            "AMBIGUO": BestClienteMap.Estado.AMBIGUO,
            "SIN_CANDIDATO": BestClienteMap.Estado.SIN_CANDIDATO,
            "PENDIENTE": BestClienteMap.Estado.PENDIENTE,
        }.get(row.status, BestClienteMap.Estado.PENDIENTE)

        obj, was_created = BestClienteMap.objects.update_or_create(
            base_empresa=base_empresa,
            best_cliente=key[0],
            best_cuit=key[1],
            defaults={
                "ordenes_abiertas": row.ordenes_abiertas,
                "estado": estado,
                "score": row.score,
                "razon": (row.razon or "")[:255],
                "admin_codigo": row.admin_codigo,
                "admin_nombre": (row.admin_nombre or "")[:255],
                "alt1_codigo": row.alt1_codigo,
                "alt1_nombre": (row.alt1_nombre or "")[:255],
                "alt1_score": row.alt1_score,
                "validado": False,
                "validado_por": "",
                "validado_en": None,
                **_FLAGS_ALCANCE_ABIERTO,
            },
        )
        if was_created:
            created += 1
        else:
            updated += 1

    for key, prev in preservados.items():
        if key not in vistos:
            for k, v in _FLAGS_ALCANCE_HISTORICO_CLI.items():
                setattr(prev, k, v)
            prev.save(
                update_fields=[
                    "requerido_migracion",
                    "en_snapshot_abierto",
                    "origen_requerimiento",
                    "actualizado_en",
                ]
            )

    for obj in BestClienteMap.objects.filter(base_empresa=base_empresa).exclude(
        estado__in=[BestClienteMap.Estado.VALIDADO, BestClienteMap.Estado.DESCARTADO]
    ):
        if (obj.best_cliente, obj.best_cuit) not in vistos:
            obj.delete()

    parity = refresh_parity_counters(base_empresa)
    parity.save()
    return {
        "created": created,
        "updated": updated,
        "preserved": preserved,
        "total": len(matches),
        "parity": parity,
    }


def resumen_clientes(base_empresa: str) -> dict[str, Any]:
    qs = BestClienteMap.objects.filter(base_empresa=base_empresa)
    by_estado = Counter(qs.values_list("estado", flat=True))
    pendientes = qs.filter(requerido_migracion=True).exclude(
        estado__in=[BestClienteMap.Estado.VALIDADO, BestClienteMap.Estado.DESCARTADO]
    ).count()
    categorias = _conteo_categorias_migracion(qs)
    return {
        "total": qs.count(),
        "por_estado": dict(by_estado),
        "pendientes": pendientes,
        "validados": by_estado.get(BestClienteMap.Estado.VALIDADO, 0),
        "inferidos": by_estado.get(BestClienteMap.Estado.INFERIDO, 0),
        "ambiguos": by_estado.get(BestClienteMap.Estado.AMBIGUO, 0),
        "sin_candidato": by_estado.get(BestClienteMap.Estado.SIN_CANDIDATO, 0),
        **categorias,
    }



def refresh_parity_counters(base_empresa: str) -> BestMigrationParity:
    parity, _ = BestMigrationParity.objects.get_or_create(base_empresa=base_empresa)
    # Gate de pedidos: solo SKUs en pedidos abiertos (no stock en depósito).
    arts = BestArticuloMap.objects.filter(
        base_empresa=base_empresa,
        requerido_migracion=True,
        origen_requerimiento=BestArticuloMap.OrigenRequerimiento.PEDIDO_ABIERTO,
    )
    parity.articulos_total = arts.count()
    parity.articulos_resueltos = sum(1 for a in arts if a.resuelto_para_migracion)

    clis = BestClienteMap.objects.filter(base_empresa=base_empresa, requerido_migracion=True)
    parity.clientes_total = clis.count()
    parity.clientes_resueltos = sum(1 for c in clis if c.resuelto_para_migracion)

    deps = BestDepositoMap.objects.filter(base_empresa=base_empresa, requerido_migracion=True)
    parity.depositos_total = deps.count()
    parity.depositos_resueltos = sum(1 for d in deps if d.resuelto_para_migracion)

    stock = BestStockInicialMap.objects.filter(base_empresa=base_empresa, requerido_migracion=True)
    parity.stock_inicial_total = stock.count()
    parity.stock_inicial_resueltos = sum(1 for s in stock if s.resuelto_para_migracion)

    parity.refresh_gate()
    return parity


def resumen_articulos(base_empresa: str) -> dict[str, Any]:
    qs = BestArticuloMap.objects.filter(base_empresa=base_empresa)
    by_estado = Counter(qs.values_list("estado", flat=True))
    estados_resueltos = [
        BestArticuloMap.Estado.VALIDADO,
        BestArticuloMap.Estado.DESCARTADO,
    ]
    ped = qs.filter(
        requerido_migracion=True,
        origen_requerimiento=BestArticuloMap.OrigenRequerimiento.PEDIDO_ABIERTO,
    )
    stock = qs.filter(
        requerido_migracion=True,
        origen_requerimiento=BestArticuloMap.OrigenRequerimiento.STOCK_DEPOSITO,
    )
    ped_pendientes = ped.exclude(estado__in=estados_resueltos).count()
    stock_pendientes = stock.exclude(estado__in=estados_resueltos).count()
    categorias = _conteo_categorias_migracion(qs)
    return {
        "total": qs.count(),
        "por_estado": dict(by_estado),
        # Pendientes del gate = solo pedidos abiertos.
        "pendientes": ped_pendientes,
        "validados": by_estado.get(BestArticuloMap.Estado.VALIDADO, 0),
        "descartados": by_estado.get(BestArticuloMap.Estado.DESCARTADO, 0),
        "ambiguos": by_estado.get(BestArticuloMap.Estado.AMBIGUO, 0),
        "sin_candidato": by_estado.get(BestArticuloMap.Estado.SIN_CANDIDATO, 0),
        "sin_match": by_estado.get(BestArticuloMap.Estado.SIN_MATCH, 0),
        "conflictos": by_estado.get(BestArticuloMap.Estado.CONFLICTO_1_A_N, 0),
        **categorias,
        "necesarios_pendientes": ped_pendientes,
        "necesarios_pendientes_pedido": ped_pendientes,
        "necesarios_pendientes_stock": stock_pendientes,
        "cumplen_pedido": categorias.get("cumplen", 0),
        "requeridos_pedido_total": ped.count(),
        "requeridos_pedido_resueltos": sum(1 for a in ped if a.resuelto_para_migracion),
        "requeridos_stock_total": stock.count(),
        "requeridos_stock_resueltos": sum(1 for a in stock if a.resuelto_para_migracion),
    }


def _detail_hub_dominio(resumen: dict[str, Any], parity_resueltos: int, parity_total: int) -> str:
    pendientes = resumen.get("requeridos_pendientes", 0)
    fuera = resumen.get("fuera_alcance", 0)
    return (
        f"{parity_resueltos}/{parity_total} requeridos resueltos · "
        f"{pendientes} pendientes · {fuera} fuera de alcance"
    )


def hub_context(base_empresa: str) -> dict[str, Any]:
    parity = refresh_parity_counters(base_empresa)
    parity.save()
    art = resumen_articulos(base_empresa)
    cli = resumen_clientes(base_empresa)
    dep = resumen_depositos(base_empresa)
    stk = resumen_stock_inicial(base_empresa)
    domains = []
    for d in DOMAINS:
        if d.codigo == "articulos":
            ok = parity.articulos_ok
            detail = _detail_hub_dominio(art, parity.articulos_resueltos, parity.articulos_total)
        elif d.codigo == "clientes":
            ok = parity.clientes_ok
            detail = _detail_hub_dominio(cli, parity.clientes_resueltos, parity.clientes_total)
        elif d.codigo == "unidades":
            ok = parity.unidades_ok
            detail = "Confirmado" if ok else "Pendiente de confirmación manual"
        elif d.codigo == "depositos":
            ok = parity.depositos_ok
            detail = _detail_hub_dominio(dep, parity.depositos_resueltos, parity.depositos_total)
        elif d.codigo == "stock_inicial":
            ok = parity.stock_inicial_ok
            detail = _detail_hub_dominio(stk, parity.stock_inicial_resueltos, parity.stock_inicial_total)
        elif d.codigo == "stock_reserva":
            res = resumen_stock_reserva_admin(base_empresa)
            ok = res.get("articulos_con_reserva", 0) > 0
            detail = (
                f"{res.get('articulos_con_reserva', 0)} artículos con reserva · "
                f"suma {res.get('suma_reserva', 0):.0f} pares"
            )
        elif d.codigo == "operarios":
            ok = parity.operarios_ok
            detail = "Opcional para sembrar PED"
        else:
            ok = False
            detail = "—"
        domains.append(
            {
                "codigo": d.codigo,
                "nombre": d.nombre,
                "obligatorio": d.obligatorio_para_pedidos,
                "descripcion": d.descripcion,
                "fuente_best": d.fuente_best,
                "destino_admin": d.destino_admin,
                "estado_modulo": d.estado_modulo,
                "ok": ok,
                "detail": detail,
            }
        )
    required = domains_required_for_orders()
    res_reserva = resumen_stock_reserva_admin(base_empresa)
    return {
        "parity": parity,
        "articulos_resumen": art,
        "clientes_resumen": cli,
        "depositos_resumen": dep,
        "stock_inicial_resumen": stk,
        "stock_reserva_resumen": res_reserva,
        "domains": domains,
        "required_codes": [d.codigo for d in required],
        "migracion_habilitada": parity.migracion_habilitada,
        "dict_version": DICT_VERSION,
    }


def validar_articulo(
    *,
    base_empresa: str,
    best_id: str,
    admin_idart: int | None,
    usuario: str,
    notas: str = "",
) -> BestArticuloMap:
    obj = BestArticuloMap.objects.get(base_empresa=base_empresa, best_id_articulo=best_id)
    if not admin_idart:
        raise ValueError("Debés indicar un IDArt de AdministraNET para validar.")
    # enriquecer nombre desde Admin si es posible
    nombre = obj.admin_nombre
    id_manual = obj.admin_id_manual
    try:
        arts = _load_admin_articulos(base_empresa)
        hit = next((a for a in arts if int(a["IDArt"]) == int(admin_idart)), None)
        if hit:
            nombre = hit.get("NombreArticulo") or nombre
            id_manual = (hit.get("id_manual") or "").strip()
    except Exception:
        logger.exception("No se pudo enriquecer artículo Admin %s", admin_idart)

    obj.admin_idart = int(admin_idart)
    obj.admin_nombre = (nombre or "")[:255]
    obj.admin_id_manual = (id_manual or "")[:64]
    obj.estado = BestArticuloMap.Estado.VALIDADO
    obj.validado = True
    obj.validado_por = (usuario or "")[:64]
    obj.validado_en = timezone.now()
    obj.notas = notas or obj.notas
    obj.save()
    refresh_parity_counters(base_empresa).save()
    return obj


def descartar_articulo(*, base_empresa: str, best_id: str, usuario: str, notas: str = "") -> BestArticuloMap:
    obj = BestArticuloMap.objects.get(base_empresa=base_empresa, best_id_articulo=best_id)
    obj.estado = BestArticuloMap.Estado.DESCARTADO
    obj.validado = True
    obj.validado_por = (usuario or "")[:64]
    obj.validado_en = timezone.now()
    obj.notas = notas or obj.notas
    obj.save()
    refresh_parity_counters(base_empresa).save()
    return obj


def aceptar_inferido(*, base_empresa: str, best_id: str, usuario: str) -> BestArticuloMap:
    obj = BestArticuloMap.objects.get(base_empresa=base_empresa, best_id_articulo=best_id)
    if not obj.admin_idart:
        raise ValueError("No hay IDArt inferido para aceptar.")
    return validar_articulo(
        base_empresa=base_empresa,
        best_id=best_id,
        admin_idart=obj.admin_idart,
        usuario=usuario,
        notas=obj.notas or "",
    )


def _nombre_articulo_desde_best(obj: BestArticuloMap) -> str:
    """Nombre Admin: preferir descripción BEST; si falta, componer con attrs."""
    nombre = (obj.best_articulo or "").strip()
    if nombre:
        return nombre[:255]
    partes: list[str] = []
    modelos = (obj.best_modelos or "").split("|")
    if modelos and modelos[0].strip():
        partes.append(modelos[0].strip())
    if (obj.best_talle or "").strip():
        partes.append(f"T{(obj.best_talle or '').strip()}")
    if (obj.best_marca or "").strip():
        partes.append((obj.best_marca or "").strip())
    if (obj.best_colores or "").strip():
        partes.append((obj.best_colores or "").strip().replace("/", " "))
    pack = (obj.best_pack or "").strip()
    if pack == "1":
        partes.append("1Par")
    elif pack:
        partes.append(f"{pack}P")
    return (" ".join(partes) or obj.best_id_articulo)[:255]


def _cod_art_prov_desde_best(obj: BestArticuloMap) -> str:
    variants = [v.strip() for v in (obj.best_variant_codes or "").split("|") if v.strip()]
    if variants:
        return variants[0][:128]
    codigo = (obj.best_codigo or "").strip()
    if codigo:
        return codigo[:128]
    return "-"


def _fetch_best_precio_venta(best_id: str) -> dict[str, Any]:
    """
    Precio de venta maestro BEST para un SKU.

    Prioridad:
      1) MC.MCSTDC en centro de costo 3000 (Cliente Genérico) si > 0
      2) REP_INVENTARIOS.Precio (MAX por SKU) si > 0

    No usa precio de línea de pedido (puede ser 0 o con descuento por cliente).
    Costo unitario no está disponible de forma confiable en BEST.
    """
    mid = (best_id or "").strip()
    if not mid:
        return {"precio": None, "fuente": None}
    conn = connect_best()
    try:
        mc_rows = fetch_dict(
            conn,
            """
            SELECT TOP 1 MCSTDC AS precio
            FROM MC
            WHERE MCMMID = %s AND MCCCID = 3000 AND COALESCE(MCSTDC, 0) > 0
            """,
            (mid,),
        )
        if mc_rows:
            precio = to_decimal_or_none(mc_rows[0].get("precio"))
            if precio is not None and precio > 0:
                return {"precio": precio, "fuente": "MC.MCSTDC@3000"}

        inv_rows = fetch_dict(
            conn,
            """
            SELECT TOP 1 MAX(COALESCE(Precio, 0)) AS precio
            FROM REP_INVENTARIOS
            WHERE [Id Articulo] = %s
            """,
            (mid,),
        )
        if inv_rows:
            precio = to_decimal_or_none(inv_rows[0].get("precio"))
            if precio is not None and precio > 0:
                return {"precio": precio, "fuente": "REP_INVENTARIOS.Precio"}
    finally:
        conn.close()
    return {"precio": None, "fuente": None}


def alta_articulo_desde_best(
    *, base_empresa: str, best_id: str, usuario: str
) -> dict[str, Any]:
    """
    Da de alta el SKU BEST en articulo (MySQL) y valida el mapeo 1:1.
    Pensado para estados SIN_CANDIDATO / SIN_MATCH sin IDArt.
    Incluye Precio1V desde BEST cuando existe; PrecioCosto queda 0.
    Completa IDSubRubro, barra CODE128, UM=1, bulto desde pack y marca.
    """
    from core.services.administranet_articulo import (
        bulto_desde_pack,
        crear_articulo,
        resolver_codigo_marca,
    )

    obj = BestArticuloMap.objects.get(base_empresa=base_empresa, best_id_articulo=best_id)
    if obj.estado == BestArticuloMap.Estado.VALIDADO and obj.admin_idart:
        raise ValueError(f"{best_id} ya está validado con IDArt {obj.admin_idart}.")
    if obj.estado == BestArticuloMap.Estado.DESCARTADO:
        raise ValueError(f"{best_id} está descartado; no se puede dar de alta.")
    if obj.admin_idart:
        raise ValueError(
            f"{best_id} ya tiene candidato IDArt {obj.admin_idart}. "
            "Usá «Aceptar inferido» o «Asignar»."
        )

    precio_info = _fetch_best_precio_venta(best_id)
    precio = precio_info.get("precio")
    overrides: dict[str, Any] = {
        "id_unimed": 1,
        "cantidad_promedio_bulto": bulto_desde_pack(obj.best_pack),
    }

    marca = resolver_codigo_marca(
        base_empresa,
        best_marca=obj.best_marca or "",
        best_id=obj.best_id_articulo,
    )
    if marca is not None:
        overrides["CodigoMarca"] = marca
    if precio is not None and precio > 0:
        # Lista 1 = precio estándar BEST; listas 2–5 igual al alta (sin listas BEST).
        overrides.update(
            {
                "Precio1V": precio,
                "Precio2V": precio,
                "Precio3V": precio,
                "Precio4V": precio,
                "Precio5V": precio,
            }
        )

    creado = crear_articulo(
        base_empresa=base_empresa,
        id_manual=obj.best_id_articulo,
        nombre_articulo=_nombre_articulo_desde_best(obj),
        cod_art_prov=_cod_art_prov_desde_best(obj),
        detalle=(
            f"Alta desde migración BEST ({obj.origen_requerimiento}). "
            f"MMID={obj.best_id_articulo}; código={obj.best_codigo or '-'}"
            + (
                f"; Precio1V={precio} ({precio_info.get('fuente')})"
                if precio is not None and precio > 0
                else "; Precio1V=0 (sin precio maestro BEST)"
            )
        ),
        tipo_art_fab="Terminado",
        overrides=overrides,
    )
    idart = int(creado["idart"])
    validar_articulo(
        base_empresa=base_empresa,
        best_id=best_id,
        admin_idart=idart,
        usuario=usuario,
        notas=(
            f"Alta automática desde BEST por {usuario}. "
            f"CodigoArticuloT={creado.get('codigo_articulo_t')}"
            + (
                f"; Precio1V={precio} ({precio_info.get('fuente')})"
                if precio is not None and precio > 0
                else "; sin precio BEST"
            )
        ),
    )
    return {
        "best_id": best_id,
        "idart": idart,
        "codigo_articulo_t": creado.get("codigo_articulo_t"),
        "stock_depositos_creados": creado.get("stock_depositos_creados", 0),
        "nombre": creado.get("nombre"),
        "precio1v": precio,
        "precio_fuente": precio_info.get("fuente"),
    }


def alta_articulos_seleccionados(
    *, base_empresa: str, best_ids: list[str], usuario: str
) -> dict[str, Any]:
    """Alta en lote de SKUs sin candidato (omite los que ya tienen IDArt o están resueltos)."""
    creados = 0
    omitidos = 0
    errores: list[str] = []
    detalles: list[dict[str, Any]] = []
    for raw in best_ids:
        best_id = (raw or "").strip()
        if not best_id:
            continue
        try:
            obj = BestArticuloMap.objects.get(
                base_empresa=base_empresa, best_id_articulo=best_id
            )
            if obj.estado in (
                BestArticuloMap.Estado.VALIDADO,
                BestArticuloMap.Estado.DESCARTADO,
            ):
                omitidos += 1
                continue
            if obj.admin_idart:
                omitidos += 1
                continue
            det = alta_articulo_desde_best(
                base_empresa=base_empresa, best_id=best_id, usuario=usuario
            )
            creados += 1
            detalles.append(det)
        except BestArticuloMap.DoesNotExist:
            omitidos += 1
        except Exception as exc:
            errores.append(f"{best_id}: {exc}")
    refresh_parity_counters(base_empresa).save()
    return {
        "creados": creados,
        "omitidos": omitidos,
        "errores": errores,
        "detalles": detalles,
    }


def marcar_unidades_ok(base_empresa: str, ok: bool = True) -> BestMigrationParity:
    parity, _ = BestMigrationParity.objects.get_or_create(base_empresa=base_empresa)
    parity.unidades_ok = bool(ok)
    parity.refresh_gate()
    parity.save()
    return parity


def aceptar_inferidos_altos_articulos(*, base_empresa: str, usuario: str) -> dict[str, Any]:
    """Valida en lote INFERIDO_ALTO de pedidos abiertos (gate de migración)."""
    qs = BestArticuloMap.objects.filter(
        base_empresa=base_empresa,
        requerido_migracion=True,
        origen_requerimiento=BestArticuloMap.OrigenRequerimiento.PEDIDO_ABIERTO,
        estado=BestArticuloMap.Estado.INFERIDO_ALTO,
        admin_idart__isnull=False,
    )
    n = 0
    for obj in qs:
        aceptar_inferido(base_empresa=base_empresa, best_id=obj.best_id_articulo, usuario=usuario)
        n += 1
    refresh_parity_counters(base_empresa).save()
    return {"aceptados": n}


def aceptar_articulos_seleccionados(
    *, base_empresa: str, best_ids: list[str], usuario: str
) -> dict[str, Any]:
    """Acepta inferidos de los SKUs indicados (deben tener admin_idart)."""
    aceptados = 0
    omitidos = 0
    errores: list[str] = []
    for raw in best_ids:
        best_id = (raw or "").strip()
        if not best_id:
            continue
        try:
            obj = BestArticuloMap.objects.get(
                base_empresa=base_empresa, best_id_articulo=best_id
            )
            if obj.estado in (
                BestArticuloMap.Estado.VALIDADO,
                BestArticuloMap.Estado.DESCARTADO,
            ):
                omitidos += 1
                continue
            if not obj.admin_idart:
                omitidos += 1
                continue
            aceptar_inferido(base_empresa=base_empresa, best_id=best_id, usuario=usuario)
            aceptados += 1
        except BestArticuloMap.DoesNotExist:
            omitidos += 1
        except Exception as exc:
            errores.append(f"{best_id}: {exc}")
    refresh_parity_counters(base_empresa).save()
    return {"aceptados": aceptados, "omitidos": omitidos, "errores": errores}


def validar_cliente(
    *,
    base_empresa: str,
    map_id: int,
    admin_codigo: int | None,
    usuario: str,
    notas: str = "",
) -> BestClienteMap:
    obj = BestClienteMap.objects.get(pk=map_id, base_empresa=base_empresa)
    if not admin_codigo:
        raise ValueError("Debés indicar un Código de cliente AdministraNET.")
    nombre = obj.admin_nombre
    try:
        clients = _load_admin_clientes(base_empresa)
        hit = next((c for c in clients if int(c["Codigo"]) == int(admin_codigo)), None)
        if hit:
            nombre = hit.get("nombre_cliente") or nombre
    except Exception:
        logger.exception("No se pudo enriquecer cliente Admin %s", admin_codigo)

    obj.admin_codigo = int(admin_codigo)
    obj.admin_nombre = (nombre or "")[:255]
    obj.estado = BestClienteMap.Estado.VALIDADO
    obj.validado = True
    obj.validado_por = (usuario or "")[:64]
    obj.validado_en = timezone.now()
    obj.notas = notas or obj.notas
    obj.save()
    refresh_parity_counters(base_empresa).save()
    return obj


def aceptar_inferido_cliente(*, base_empresa: str, map_id: int, usuario: str) -> BestClienteMap:
    obj = BestClienteMap.objects.get(pk=map_id, base_empresa=base_empresa)
    if not obj.admin_codigo:
        raise ValueError("El inferido no tiene Código candidato.")
    return validar_cliente(
        base_empresa=base_empresa,
        map_id=map_id,
        admin_codigo=obj.admin_codigo,
        usuario=usuario,
        notas="Aceptado desde inferencia automática",
    )


def descartar_cliente(*, base_empresa: str, map_id: int, usuario: str, notas: str = "") -> BestClienteMap:
    obj = BestClienteMap.objects.get(pk=map_id, base_empresa=base_empresa)
    obj.estado = BestClienteMap.Estado.DESCARTADO
    obj.validado = True
    obj.validado_por = (usuario or "")[:64]
    obj.validado_en = timezone.now()
    obj.notas = notas or obj.notas
    obj.save()
    refresh_parity_counters(base_empresa).save()
    return obj


def aceptar_inferidos_clientes(*, base_empresa: str, usuario: str) -> dict[str, Any]:
    qs = BestClienteMap.objects.filter(
        base_empresa=base_empresa,
        requerido_migracion=True,
        estado=BestClienteMap.Estado.INFERIDO,
        admin_codigo__isnull=False,
        score__gte=85,
    )
    n = 0
    for obj in qs:
        aceptar_inferido_cliente(base_empresa=base_empresa, map_id=obj.pk, usuario=usuario)
        n += 1
    refresh_parity_counters(base_empresa).save()
    return {"aceptados": n}


def aceptar_clientes_seleccionados(
    *, base_empresa: str, map_ids: list[int], usuario: str
) -> dict[str, Any]:
    aceptados = 0
    omitidos = 0
    errores: list[str] = []
    for mid in map_ids:
        try:
            obj = BestClienteMap.objects.get(pk=mid, base_empresa=base_empresa)
            if obj.estado in (
                BestClienteMap.Estado.VALIDADO,
                BestClienteMap.Estado.DESCARTADO,
            ):
                omitidos += 1
                continue
            if not obj.admin_codigo:
                omitidos += 1
                continue
            aceptar_inferido_cliente(base_empresa=base_empresa, map_id=mid, usuario=usuario)
            aceptados += 1
        except BestClienteMap.DoesNotExist:
            omitidos += 1
        except Exception as exc:
            errores.append(f"{mid}: {exc}")
    refresh_parity_counters(base_empresa).save()
    return {"aceptados": aceptados, "omitidos": omitidos, "errores": errores}


def _fetch_best_depositos_vigentes() -> list[dict]:
    """Depósitos BEST con saldo ≠ 0 y/o usados en pedidos abiertos."""
    conn = connect_best()
    try:
        inv_rows = fetch_dict(
            conn,
            """
            SELECT [Id Deposito] AS id_dep, Deposito AS nombre,
                   SUM(COALESCE(Stock, 0)) AS stock_pares,
                   COUNT(DISTINCT [Id Articulo]) AS skus
            FROM REP_INVENTARIOS
            WHERE COALESCE(Stock, 0) <> 0
            GROUP BY [Id Deposito], Deposito
            """,
        )
        ped_rows = fetch_dict(
            conn,
            """
            SELECT DISTINCT [Deposito Origen] AS nombre
            FROM REP_ORDENES_COMBINADO
            WHERE Finalizada = 0 AND Pendiente > 0
              AND COALESCE([Deposito Origen], '') <> ''
            """,
        )
    finally:
        conn.close()

    by_id: dict[int, dict] = {}
    by_name: dict[str, int] = {}
    for r in inv_rows:
        dep_id = to_int_or_none(r.get("id_dep"))
        if not dep_id:
            continue
        nombre = (r.get("nombre") or "").strip()
        by_id[dep_id] = {
            "id_dep": dep_id,
            "nombre": nombre,
            "stock_pares": r.get("stock_pares"),
            "skus": r.get("skus"),
            "origen": BestDepositoMap.OrigenRequerimiento.STOCK_DEPOSITO,
        }
        if nombre:
            by_name[norm_text(nombre)] = dep_id

    for r in ped_rows:
        nombre = (r.get("nombre") or "").strip()
        if not nombre:
            continue
        dep_id = by_name.get(norm_text(nombre))
        if not dep_id:
            for known_id in BEST_DEPOSITO_TIPO_MPR:
                inv_hit = by_id.get(known_id)
                if inv_hit and norm_text(inv_hit.get("nombre")) == norm_text(nombre):
                    dep_id = known_id
                    break
            if not dep_id:
                for known_id in BEST_DEPOSITO_TIPO_MPR:
                    inv_hit = by_id.get(known_id)
                    if inv_hit and (
                        norm_text(nombre) in norm_text(inv_hit.get("nombre"))
                        or norm_text(inv_hit.get("nombre")) in norm_text(nombre)
                    ):
                        dep_id = known_id
                        break
        if dep_id and dep_id in by_id:
            if by_id[dep_id]["origen"] != BestDepositoMap.OrigenRequerimiento.STOCK_DEPOSITO:
                by_id[dep_id]["origen"] = BestDepositoMap.OrigenRequerimiento.PEDIDO_ABIERTO
        elif dep_id:
            by_id[dep_id] = {
                "id_dep": dep_id,
                "nombre": nombre,
                "stock_pares": 0,
                "skus": 0,
                "origen": BestDepositoMap.OrigenRequerimiento.PEDIDO_ABIERTO,
            }

    return list(by_id.values())


def _fetch_best_inventario_agregado() -> list[dict]:
    conn = connect_best()
    try:
        return fetch_dict(
            conn,
            """
            SELECT [Id Articulo] AS id_art, MAX(Articulo) AS articulo,
                   [Id Deposito] AS id_dep, MAX(Deposito) AS deposito,
                   SUM(COALESCE(Stock, 0)) AS stock_pares,
                   SUM(COALESCE(Docenas, 0)) AS docenas
            FROM REP_INVENTARIOS
            WHERE COALESCE(Stock, 0) <> 0
            GROUP BY [Id Articulo], [Id Deposito]
            """,
        )
    finally:
        conn.close()


def _load_admin_stock_deposito(base_empresa: str) -> dict[tuple[int, int], Any]:
    with mysql_cursor(base_empresa, dict_cursor=True) as cur:
        cur.execute(
            """
            SELECT id_articulo, id_deposito, COALESCE(saldo, 0) AS saldo
            FROM stock_deposito
            """
        )
        rows = cur.fetchall()
    out: dict[tuple[int, int], Any] = {}
    for r in rows:
        id_art = to_int_or_none(r.get("id_articulo"))
        id_dep = to_int_or_none(r.get("id_deposito"))
        if id_art and id_dep:
            out[(id_art, id_dep)] = to_decimal_or_none(r.get("saldo"))
    return out


def _load_admin_articulos_para_stock(
    base_empresa: str, ids_articulo: list[int]
) -> dict[int, dict[str, str]]:
    """Carga código y descripción canónicos para renglones de Stock Inicial."""
    ids_validos = sorted({id_art for id_art in ids_articulo if id_art is not None})
    if not ids_validos:
        return {}
    placeholders = ", ".join(["%s"] * len(ids_validos))
    with mysql_cursor(base_empresa, dict_cursor=True) as cur:
        cur.execute(
            f"""
            SELECT IDArt,
                   TRIM(COALESCE(CodigoArticuloT, '')) AS codigo_articulo,
                   TRIM(COALESCE(NombreArticulo, '')) AS nombre_articulo
            FROM articulo
            WHERE IDArt IN ({placeholders})
            """,
            ids_validos,
        )
        rows = cur.fetchall()
    return {
        id_art: {
            "codigo_articulo": str_or_default(row.get("codigo_articulo"), ""),
            "nombre_articulo": str_or_default(row.get("nombre_articulo"), ""),
        }
        for row in rows
        if (id_art := to_int_or_none(row.get("IDArt"))) is not None
    }


@transaction.atomic
def sincronizar_depositos_best(base_empresa: str) -> dict[str, Any]:
    best_rows = _fetch_best_depositos_vigentes()
    admin_deps = listar_depositos_config(base_empresa)
    matches = match_depositos(best_rows=best_rows, admin_depositos=admin_deps)
    match_by_id = {m.best_id_deposito: m for m in matches}

    preservados = {
        m.best_id_deposito: m
        for m in BestDepositoMap.objects.filter(
            base_empresa=base_empresa,
            estado__in=[BestDepositoMap.Estado.VALIDADO, BestDepositoMap.Estado.DESCARTADO],
        )
    }

    created = updated = preserved = 0
    vistos: set[int] = set()
    origen_by_id = {int(r["id_dep"]): r.get("origen") for r in best_rows}

    for row in best_rows:
        dep_id = int(row["id_dep"])
        vistos.add(dep_id)
        prev = preservados.get(dep_id)
        origen = origen_by_id.get(dep_id) or BestDepositoMap.OrigenRequerimiento.STOCK_DEPOSITO
        flags = (
            _FLAGS_ALCANCE_PEDIDO_DEP
            if origen == BestDepositoMap.OrigenRequerimiento.PEDIDO_ABIERTO
            else _FLAGS_ALCANCE_STOCK_DEP
        )

        if prev:
            prev.best_nombre = (row.get("nombre") or "")[:255]
            prev.tipo_mpr_esperado = (
                BEST_DEPOSITO_TIPO_MPR.get(dep_id) or prev.tipo_mpr_esperado or ""
            )[:32]
            for k, v in flags.items():
                setattr(prev, k, v)
            prev.save()
            preserved += 1
            continue

        m = match_by_id.get(dep_id)
        if not m:
            continue

        estado_map = {
            "INFERIDO": BestDepositoMap.Estado.INFERIDO,
            "SIN_CANDIDATO": BestDepositoMap.Estado.SIN_CANDIDATO,
            "PENDIENTE": BestDepositoMap.Estado.PENDIENTE,
        }
        estado = estado_map.get(m.status, BestDepositoMap.Estado.PENDIENTE)

        obj, was_created = BestDepositoMap.objects.update_or_create(
            base_empresa=base_empresa,
            best_id_deposito=dep_id,
            defaults={
                "best_nombre": (row.get("nombre") or m.best_nombre or "")[:255],
                "tipo_mpr_esperado": (m.tipo_mpr_esperado or "")[:32],
                "estado": estado,
                "score": m.score,
                "razon": (m.razon or "")[:512],
                "admin_cod_deposito": m.admin_cod_deposito,
                "admin_nombre": (m.admin_nombre or "")[:255],
                "admin_tipo_mpr": (m.admin_tipo_mpr or "")[:32],
                "validado": False,
                "validado_por": "",
                "validado_en": None,
                **flags,
            },
        )
        if was_created:
            created += 1
        else:
            updated += 1

    for dep_id, prev in preservados.items():
        if dep_id not in vistos:
            for k, v in _FLAGS_ALCANCE_HISTORICO_DEP.items():
                setattr(prev, k, v)
            prev.save(
                update_fields=[
                    "requerido_migracion",
                    "en_snapshot_abierto",
                    "origen_requerimiento",
                    "actualizado_en",
                ]
            )

    BestDepositoMap.objects.filter(base_empresa=base_empresa).exclude(
        best_id_deposito__in=vistos
    ).exclude(
        estado__in=[BestDepositoMap.Estado.VALIDADO, BestDepositoMap.Estado.DESCARTADO]
    ).delete()

    parity = refresh_parity_counters(base_empresa)
    parity.save()
    return {
        "created": created,
        "updated": updated,
        "preserved": preserved,
        "total": len(best_rows),
        "parity": parity,
    }


def resumen_depositos(base_empresa: str) -> dict[str, Any]:
    qs = BestDepositoMap.objects.filter(base_empresa=base_empresa)
    by_estado = Counter(qs.values_list("estado", flat=True))
    pendientes = qs.filter(requerido_migracion=True).exclude(
        estado__in=[BestDepositoMap.Estado.VALIDADO, BestDepositoMap.Estado.DESCARTADO]
    ).count()
    categorias = _conteo_categorias_migracion(qs)
    return {
        "total": qs.count(),
        "por_estado": dict(by_estado),
        "pendientes": pendientes,
        "validados": by_estado.get(BestDepositoMap.Estado.VALIDADO, 0),
        "inferidos": by_estado.get(BestDepositoMap.Estado.INFERIDO, 0),
        "sin_candidato": by_estado.get(BestDepositoMap.Estado.SIN_CANDIDATO, 0),
        **categorias,
    }


def _aplicar_tipo_mpr_deposito(
    base_empresa: str, cod_deposito: int, tipo_mpr_esperado: str
) -> tuple[str, str]:
    if not tipo_mpr_esperado:
        deps = listar_depositos_config(base_empresa)
        hit = next((d for d in deps if int(d["CodDeposito"]) == int(cod_deposito)), None)
        return ((hit.get("tipo_mpr") or "") if hit else "", "")

    deps = listar_depositos_config(base_empresa)
    hit = next((d for d in deps if int(d["CodDeposito"]) == int(cod_deposito)), None)
    actual = ((hit.get("tipo_mpr") or "").strip() if hit else "")
    if actual == tipo_mpr_esperado:
        return actual, ""

    ok, err = actualizar_deposito_tipo_mpr(base_empresa, cod_deposito, tipo_mpr_esperado)
    if not ok:
        return actual, err or "No se pudo actualizar tipo_mpr."
    deps = listar_depositos_config(base_empresa)
    hit = next((d for d in deps if int(d["CodDeposito"]) == int(cod_deposito)), None)
    return ((hit.get("tipo_mpr") or tipo_mpr_esperado) if hit else tipo_mpr_esperado, "")


def validar_deposito(
    *,
    base_empresa: str,
    map_id: int,
    admin_cod_deposito: int | None,
    usuario: str,
    notas: str = "",
) -> BestDepositoMap:
    obj = BestDepositoMap.objects.get(pk=map_id, base_empresa=base_empresa)
    if not admin_cod_deposito:
        raise ValueError("Debés indicar un CodDeposito de AdministraNET.")
    nombre = obj.admin_nombre
    deps = listar_depositos_config(base_empresa)
    hit = next((d for d in deps if int(d["CodDeposito"]) == int(admin_cod_deposito)), None)
    if hit:
        nombre = hit.get("NombreDeposito") or nombre

    tipo_actual, err = _aplicar_tipo_mpr_deposito(
        base_empresa, int(admin_cod_deposito), (obj.tipo_mpr_esperado or "").strip()
    )
    if err:
        raise ValueError(err)

    obj.admin_cod_deposito = int(admin_cod_deposito)
    obj.admin_nombre = (nombre or "")[:255]
    obj.admin_tipo_mpr = (tipo_actual or "")[:32]
    obj.estado = BestDepositoMap.Estado.VALIDADO
    obj.validado = True
    obj.validado_por = (usuario or "")[:64]
    obj.validado_en = timezone.now()
    obj.notas = notas or obj.notas
    obj.save()
    refresh_parity_counters(base_empresa).save()
    return obj


def aceptar_inferido_deposito(*, base_empresa: str, map_id: int, usuario: str) -> BestDepositoMap:
    obj = BestDepositoMap.objects.get(pk=map_id, base_empresa=base_empresa)
    if not obj.admin_cod_deposito:
        raise ValueError("El inferido no tiene CodDeposito candidato.")
    return validar_deposito(
        base_empresa=base_empresa,
        map_id=map_id,
        admin_cod_deposito=obj.admin_cod_deposito,
        usuario=usuario,
        notas="Aceptado desde inferencia automática",
    )


def descartar_deposito(*, base_empresa: str, map_id: int, usuario: str, notas: str = "") -> BestDepositoMap:
    obj = BestDepositoMap.objects.get(pk=map_id, base_empresa=base_empresa)
    obj.estado = BestDepositoMap.Estado.DESCARTADO
    obj.validado = True
    obj.validado_por = (usuario or "")[:64]
    obj.validado_en = timezone.now()
    obj.notas = notas or obj.notas
    obj.save()
    refresh_parity_counters(base_empresa).save()
    return obj


def aceptar_inferidos_depositos(*, base_empresa: str, usuario: str) -> dict[str, Any]:
    qs = BestDepositoMap.objects.filter(
        base_empresa=base_empresa,
        requerido_migracion=True,
        estado=BestDepositoMap.Estado.INFERIDO,
        admin_cod_deposito__isnull=False,
    )
    n = 0
    for obj in qs:
        aceptar_inferido_deposito(base_empresa=base_empresa, map_id=obj.pk, usuario=usuario)
        n += 1
    refresh_parity_counters(base_empresa).save()
    return {"aceptados": n}


def aceptar_depositos_seleccionados(
    *, base_empresa: str, map_ids: list[int], usuario: str
) -> dict[str, Any]:
    aceptados = 0
    omitidos = 0
    errores: list[str] = []
    for mid in map_ids:
        try:
            obj = BestDepositoMap.objects.get(pk=mid, base_empresa=base_empresa)
            if obj.estado in (
                BestDepositoMap.Estado.VALIDADO,
                BestDepositoMap.Estado.DESCARTADO,
            ):
                omitidos += 1
                continue
            if not obj.admin_cod_deposito:
                omitidos += 1
                continue
            aceptar_inferido_deposito(base_empresa=base_empresa, map_id=mid, usuario=usuario)
            aceptados += 1
        except BestDepositoMap.DoesNotExist:
            omitidos += 1
        except Exception as exc:
            errores.append(f"{mid}: {exc}")
    refresh_parity_counters(base_empresa).save()
    return {"aceptados": aceptados, "omitidos": omitidos, "errores": errores}


@transaction.atomic
def sincronizar_stock_inicial(base_empresa: str) -> dict[str, Any]:
    articulos_inventario = asegurar_articulos_desde_inventario(base_empresa)
    inv_rows = _fetch_best_inventario_agregado()
    arts_validados = {
        m.best_id_articulo: m
        for m in BestArticuloMap.objects.filter(
            base_empresa=base_empresa,
            estado=BestArticuloMap.Estado.VALIDADO,
            admin_idart__isnull=False,
        )
    }
    deps_validados = {
        m.best_id_deposito: m
        for m in BestDepositoMap.objects.filter(
            base_empresa=base_empresa,
            estado=BestDepositoMap.Estado.VALIDADO,
            admin_cod_deposito__isnull=False,
        )
    }
    admin_saldos = _load_admin_stock_deposito(base_empresa)

    preservados = {
        (m.best_id_articulo, m.best_id_deposito): m
        for m in BestStockInicialMap.objects.filter(
            base_empresa=base_empresa,
            estado__in=[
                BestStockInicialMap.Estado.CONCILIADO,
                BestStockInicialMap.Estado.CARGADO,
                BestStockInicialMap.Estado.DESCARTADO,
            ],
        )
    }

    created = updated = preserved = 0
    vistos: set[tuple[str, int]] = set()

    for row in inv_rows:
        best_id_art = str(row.get("id_art") or "").strip()
        best_id_dep = to_int_or_none(row.get("id_dep"))
        if not best_id_art or not best_id_dep:
            continue
        stock_pares = to_decimal_or_none(row.get("stock_pares")) or 0
        if stock_pares == 0:
            continue

        key = (best_id_art, best_id_dep)
        vistos.add(key)
        prev = preservados.get(key)

        art_map = arts_validados.get(best_id_art)
        dep_map = deps_validados.get(best_id_dep)
        admin_idart = art_map.admin_idart if art_map else None
        admin_cod_dep = dep_map.admin_cod_deposito if dep_map else None
        admin_nombre = (art_map.admin_nombre if art_map else "")[:255]
        admin_dep_nombre = (dep_map.admin_nombre if dep_map else "")[:255]

        admin_saldo = None
        delta = None
        if admin_idart and admin_cod_dep:
            admin_saldo = admin_saldos.get((int(admin_idart), int(admin_cod_dep)))
            if admin_saldo is not None:
                delta = stock_pares - admin_saldo

        if prev:
            if prev.estado not in {
                BestStockInicialMap.Estado.CARGADO,
                BestStockInicialMap.Estado.DESCARTADO,
            }:
                prev.best_articulo = (row.get("articulo") or "")[:255]
                prev.best_deposito_nombre = (row.get("deposito") or "")[:255]
                prev.best_stock_pares = stock_pares
                prev.best_docenas = to_decimal_or_none(row.get("docenas"))
                prev.admin_idart = admin_idart
                prev.admin_nombre = admin_nombre
                prev.admin_cod_deposito = admin_cod_dep
                prev.admin_deposito_nombre = admin_dep_nombre
                prev.admin_saldo_actual = admin_saldo
                prev.delta_pares = delta
                prev.requerido_migracion = True
                prev.save()
            preserved += 1
            continue

        if not art_map:
            estado = BestStockInicialMap.Estado.SIN_MAPEO_ARTICULO
        elif not dep_map:
            estado = BestStockInicialMap.Estado.SIN_MAPEO_DEPOSITO
        else:
            estado = BestStockInicialMap.Estado.LISTO

        obj, was_created = BestStockInicialMap.objects.update_or_create(
            base_empresa=base_empresa,
            best_id_articulo=best_id_art,
            best_id_deposito=best_id_dep,
            defaults={
                "best_articulo": (row.get("articulo") or "")[:255],
                "best_deposito_nombre": (row.get("deposito") or "")[:255],
                "best_stock_pares": stock_pares,
                "best_docenas": to_decimal_or_none(row.get("docenas")),
                "admin_idart": admin_idart,
                "admin_nombre": admin_nombre,
                "admin_cod_deposito": admin_cod_dep,
                "admin_deposito_nombre": admin_dep_nombre,
                "admin_saldo_actual": admin_saldo,
                "delta_pares": delta,
                "estado": estado,
                "requerido_migracion": True,
                "origen_requerimiento": BestStockInicialMap.OrigenRequerimiento.STOCK_DEPOSITO,
                "validado": False,
                "validado_por": "",
                "validado_en": None,
            },
        )
        if was_created:
            created += 1
        else:
            updated += 1

    for obj in BestStockInicialMap.objects.filter(base_empresa=base_empresa).exclude(
        estado__in=[
            BestStockInicialMap.Estado.CONCILIADO,
            BestStockInicialMap.Estado.CARGADO,
            BestStockInicialMap.Estado.DESCARTADO,
        ]
    ):
        if (obj.best_id_articulo, obj.best_id_deposito) not in vistos:
            obj.delete()

    parity = refresh_parity_counters(base_empresa)
    parity.save()
    return {
        "created": created,
        "updated": updated,
        "preserved": preserved,
        "total": len(vistos),
        "articulos_inventario": articulos_inventario,
        "parity": parity,
    }


def resumen_stock_inicial(base_empresa: str) -> dict[str, Any]:
    qs = BestStockInicialMap.objects.filter(base_empresa=base_empresa)
    by_estado = Counter(qs.values_list("estado", flat=True))
    pendientes = qs.filter(requerido_migracion=True).exclude(
        estado__in=[
            BestStockInicialMap.Estado.CONCILIADO,
            BestStockInicialMap.Estado.CARGADO,
            BestStockInicialMap.Estado.DESCARTADO,
        ]
    ).count()
    con_delta = qs.filter(delta_pares__isnull=False).exclude(delta_pares=0).count()
    categorias = _conteo_categorias_migracion(qs)
    return {
        "total": qs.count(),
        "por_estado": dict(by_estado),
        "pendientes": pendientes,
        "listos": by_estado.get(BestStockInicialMap.Estado.LISTO, 0),
        "conciliados": by_estado.get(BestStockInicialMap.Estado.CONCILIADO, 0),
        "cargados": by_estado.get(BestStockInicialMap.Estado.CARGADO, 0),
        "sin_mapeo_articulo": by_estado.get(BestStockInicialMap.Estado.SIN_MAPEO_ARTICULO, 0),
        "sin_mapeo_deposito": by_estado.get(BestStockInicialMap.Estado.SIN_MAPEO_DEPOSITO, 0),
        "con_delta": con_delta,
        **categorias,
    }


def resumen_stock_reserva_admin(base_empresa: str) -> dict[str, Any]:
    """Contadores rápidos de articulo.stock_reserva en Admin (para hub)."""
    try:
        with mysql_cursor(base_empresa, dict_cursor=True) as cur:
            cur.execute(
                """
                SELECT COUNT(*) AS n,
                       COALESCE(SUM(stock_reserva), 0) AS total
                FROM articulo
                WHERE COALESCE(stock_reserva, 0) > 0
                """
            )
            row = cur.fetchone() or {}
        n = int(row.get("n") or 0)
        total = float(row.get("total") or 0)
    except Exception:
        n = 0
        total = 0.0
    return {"articulos_con_reserva": n, "suma_reserva": total}


def marcar_stock_conciliado(
    *, base_empresa: str, map_id: int, usuario: str, notas: str = ""
) -> BestStockInicialMap:
    obj = BestStockInicialMap.objects.get(pk=map_id, base_empresa=base_empresa)
    if obj.estado not in {
        BestStockInicialMap.Estado.LISTO,
        BestStockInicialMap.Estado.CONCILIADO,
    }:
        raise ValueError("Solo se puede conciliar una línea en estado LISTO.")
    if not obj.admin_idart or not obj.admin_cod_deposito:
        raise ValueError("Faltan mapeos de artículo o depósito.")
    obj.estado = BestStockInicialMap.Estado.CONCILIADO
    obj.validado = True
    obj.validado_por = (usuario or "")[:64]
    obj.validado_en = timezone.now()
    obj.notas = notas or obj.notas
    obj.save()
    refresh_parity_counters(base_empresa).save()
    return obj


def descartar_stock_linea(
    *, base_empresa: str, map_id: int, usuario: str, notas: str = ""
) -> BestStockInicialMap:
    obj = BestStockInicialMap.objects.get(pk=map_id, base_empresa=base_empresa)
    obj.estado = BestStockInicialMap.Estado.DESCARTADO
    obj.validado = True
    obj.validado_por = (usuario or "")[:64]
    obj.validado_en = timezone.now()
    obj.notas = notas or obj.notas
    obj.save()
    refresh_parity_counters(base_empresa).save()
    return obj


def cargar_stock_inicial_best(
    base_empresa: str,
    *,
    dry_run: bool = True,
    usuario: str = "",
    id_usuario: int | None = None,
    id_puesto: int | None = None,
    id_pv: int | None = None,
) -> dict[str, Any]:
    """
    Carga opening balance vía alta_movimiento (motivo 1 = Stock Inicial),
    misma lógica que /stock/ingreso-movimiento/.

    Por depósito genera uno o más MSTOCK con entradas (ES=E) por el delta
    (BEST − saldo Admin). Si Admin ya tiene ≥ BEST, no mueve stock y marca CARGADO.
    """
    from collections import defaultdict
    from datetime import date
    from decimal import Decimal

    from core.services.administranet_stock import alta_movimiento

    qs = BestStockInicialMap.objects.filter(
        base_empresa=base_empresa,
        requerido_migracion=True,
        estado__in=[
            BestStockInicialMap.Estado.LISTO,
            BestStockInicialMap.Estado.CONCILIADO,
        ],
        admin_idart__isnull=False,
        admin_cod_deposito__isnull=False,
    )
    candidatos = list(qs)
    by_dep: dict[int, list[BestStockInicialMap]] = defaultdict(list)
    for obj in candidatos:
        dep = to_int_or_none(obj.admin_cod_deposito)
        if dep:
            by_dep[dep].append(obj)

    lotes_estimados = 0
    lineas_con_delta = 0
    for objs in by_dep.values():
        n_delta = 0
        for obj in objs:
            best = to_decimal_or_none(obj.best_stock_pares) or Decimal(0)
            admin = to_decimal_or_none(obj.admin_saldo_actual) or Decimal(0)
            if best - admin > 0:
                n_delta += 1
        lineas_con_delta += n_delta
        if n_delta:
            lotes_estimados += (n_delta + 99) // 100

    if dry_run:
        return {
            "dry_run": True,
            "candidatos": len(candidatos),
            "escrituras": lineas_con_delta,
            "movimientos_estimados": lotes_estimados,
            "omitidos": len(candidatos) - lineas_con_delta,
            "via": "alta_movimiento:Stock Inicial",
        }

    uid = to_int_or_none(id_usuario)
    if not uid:
        raise ValueError(
            "Se requiere id_usuario de sesión para grabar Stock Inicial "
            "(misma lógica que /stock/ingreso-movimiento/)."
        )

    escrituras = 0
    omitidos = 0
    movimientos: list[dict[str, Any]] = []
    errores: list[str] = []
    chunk_size = 100
    fecha_hoy = date.today().isoformat()
    pv = to_int_or_none(id_pv) or 1
    articulos_admin = _load_admin_articulos_para_stock(
        base_empresa,
        [
            id_art
            for obj in candidatos
            if (id_art := to_int_or_none(obj.admin_idart)) is not None
        ],
    )

    for dep_id, objs in sorted(by_dep.items()):
        pendientes_mov: list[tuple[BestStockInicialMap, Decimal]] = []
        for obj in objs:
            best = to_decimal_or_none(obj.best_stock_pares) or Decimal(0)
            admin = to_decimal_or_none(obj.admin_saldo_actual) or Decimal(0)
            delta = best - admin
            if delta <= 0:
                # Ya en o por encima del saldo BEST: sin movimiento.
                obj.estado = BestStockInicialMap.Estado.CARGADO
                obj.validado = True
                obj.validado_por = (usuario or "")[:64]
                obj.validado_en = timezone.now()
                obj.notas = (obj.notas or "") + (
                    "" if not obj.notas else " | "
                ) + "Sin movimiento: saldo Admin ≥ BEST."
                obj.save(
                    update_fields=[
                        "estado",
                        "validado",
                        "validado_por",
                        "validado_en",
                        "notas",
                        "actualizado_en",
                    ]
                )
                omitidos += 1
                continue
            pendientes_mov.append((obj, delta))

        for i in range(0, len(pendientes_mov), chunk_size):
            chunk = pendientes_mov[i : i + chunk_size]
            renglones = []
            for obj, delta in chunk:
                id_art = to_int_or_none(obj.admin_idart)
                articulo_admin = articulos_admin.get(id_art, {})
                renglones.append(
                    {
                        "IDArt": id_art,
                        "CodigoArticulo": str_or_default(
                            articulo_admin.get("codigo_articulo"), ""
                        )[:64],
                        "Descripcion": str_or_default(
                            articulo_admin.get("nombre_articulo")
                            or obj.admin_nombre
                            or obj.best_articulo,
                            "",
                        )[:255],
                        "Cantidad": delta,
                        "entrada": delta,
                        "salida": 0,
                        "ES": "E",
                        "CodDeposito": dep_id,
                    }
                )
            ok, codigo_mov, nro_comp, mensaje, schema_errores = alta_movimiento(
                base_empresa=base_empresa,
                id_usuario=uid,
                id_puesto=to_int_or_none(id_puesto),
                cabecera={
                    "motivo_movimiento": 1,
                    "id_ref_movstock": 1,
                    "fecha": fecha_hoy,
                    "deposito_origen": dep_id,
                    "deposito_destino": dep_id,
                    # ASCII en detalle: MySQL/cliente legacy (charmap) no acepta →
                    "detalle": (
                        f"Cutover BEST -> stock inicial "
                        f"(dep {dep_id}, lote {i // chunk_size + 1})"
                    )[:255],
                    "id_pv": pv,
                },
                renglones=renglones,
            )
            if not ok:
                err = mensaje or "Error al grabar Stock Inicial."
                if schema_errores:
                    err += " Esquema incompleto para movimientos de stock."
                errores.append(f"Depósito {dep_id}: {err}")
                logger.error("cargar_stock_inicial_best dep=%s: %s", dep_id, err)
                continue

            movimientos.append(
                {
                    "deposito": dep_id,
                    "codigo_movimiento": int(codigo_mov) if codigo_mov is not None else None,
                    "nro_comprobante": nro_comp,
                    "renglones": len(chunk),
                }
            )
            for obj, _delta in chunk:
                obj.estado = BestStockInicialMap.Estado.CARGADO
                obj.validado = True
                obj.validado_por = (usuario or "")[:64]
                obj.validado_en = timezone.now()
                obj.notas = (obj.notas or "") + (
                    "" if not obj.notas else " | "
                ) + f"MSTOCK {nro_comp}"
                obj.save(
                    update_fields=[
                        "estado",
                        "validado",
                        "validado_por",
                        "validado_en",
                        "notas",
                        "actualizado_en",
                    ]
                )
                escrituras += 1

    refresh_parity_counters(base_empresa).save()
    result = {
        "dry_run": False,
        "candidatos": len(candidatos),
        "escrituras": escrituras,
        "omitidos": omitidos,
        "movimientos": movimientos,
        "via": "alta_movimiento:Stock Inicial",
    }
    if errores:
        result["errores"] = errores
    return result
