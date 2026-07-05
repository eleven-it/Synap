# -*- coding: utf-8 -*-
"""
Migra ledgers MPR desde Postgres (Django) hacia tablas mpr_* en MySQL.

Orden FK: turno → roster → parte → linea/ajuste → transicion → armado lote →
movimiento armado → lineas armado → imputacion → envio → config.

Ejemplo:
  docker exec Synap_app python manage.py migrate_mpr_ledgers_to_mysql administranet93
  docker exec Synap_app python manage.py migrate_mpr_ledgers_to_mysql administranet93 --dry-run
"""
from decimal import Decimal

from django.core.management.base import BaseCommand

from core.utils.administranet_types import to_int_or_none
from mpr.db import mysql_cursor


class Command(BaseCommand):
    help = "Copia ledgers MPR de Postgres a MySQL (mpr_*) por base_empresa."

    def add_arguments(self, parser):
        parser.add_argument("base_empresa", type=str, help="Base MySQL destino (ej. administranet93)")
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Solo reporta conteos sin escribir.",
        )

    def handle(self, *args, **options):
        from mpr.models import (
            MprArmadoLote,
            MprArmadoSurtidoLinea,
            MprArmadoSurtidoMovimiento,
            MprEmpresaConfig,
            MprEnvioProduccion,
            MprImputacionArmado,
            MprParte,
            MprParteAjuste,
            MprParteLinea,
            MprRosterDia,
            MprTransicionLote,
            MprTurno,
        )

        base = (options.get("base_empresa") or "").strip()
        dry = options.get("dry_run", False)
        if not base:
            self.stdout.write(self.style.ERROR("Indique base_empresa."))
            return

        entidades = {
            "mpr_turno": MprTurno.objects.filter(base_empresa=base).count(),
            "mpr_roster_dia": MprRosterDia.objects.filter(base_empresa=base).count(),
            "mpr_parte": MprParte.objects.filter(base_empresa=base).count(),
            "mpr_parte_linea": MprParteLinea.objects.filter(parte__base_empresa=base).count(),
            "mpr_parte_ajuste": MprParteAjuste.objects.filter(parte__base_empresa=base).count(),
            "mpr_transicion_lote": MprTransicionLote.objects.filter(base_empresa=base).count(),
            "mpr_armado_lote": MprArmadoLote.objects.filter(base_empresa=base).count(),
            "mpr_armado_mov": MprArmadoSurtidoMovimiento.objects.filter(base_empresa=base).count(),
            "mpr_armado_linea": MprArmadoSurtidoLinea.objects.filter(
                movimiento__base_empresa=base
            ).count(),
            "mpr_imputacion": MprImputacionArmado.objects.filter(base_empresa=base).count(),
            "mpr_envio_produccion": MprEnvioProduccion.objects.filter(base_empresa=base).count(),
        }

        self.stdout.write(f"Origen Postgres ({base}):")
        for k, v in entidades.items():
            self.stdout.write(f"  {k}: {v}")

        if dry:
            self.stdout.write(self.style.WARNING("Dry-run: no se escribió MySQL."))
            return

        turno_map: dict = {}
        lote_map: dict = {}
        parte_map: dict = {}

        with mysql_cursor(base) as cursor:
            for t in MprTurno.objects.filter(base_empresa=base).order_by("id"):
                cursor.execute(
                    """
                    INSERT INTO mpr_turno (nombre, hora_inicio, hora_fin, activo, creado_en)
                    VALUES (%s, %s, %s, %s, %s)
                    ON DUPLICATE KEY UPDATE id_mpr_turno = LAST_INSERT_ID(id_mpr_turno)
                    """,
                    [t.nombre, t.hora_inicio, t.hora_fin, 1 if t.activo else 0, t.creado_en],
                )
                turno_map[t.id] = int(cursor.lastrowid)

            for r in MprRosterDia.objects.filter(base_empresa=base).select_related("turno"):
                id_turno_mysql = turno_map.get(r.turno_id)
                if not id_turno_mysql:
                    continue
                cursor.execute(
                    """
                    INSERT INTO mpr_roster_dia (fecha, id_operario, id_mpr_turno, creado_en)
                    VALUES (%s, %s, %s, %s)
                    ON DUPLICATE KEY UPDATE id_mpr_turno = VALUES(id_mpr_turno)
                    """,
                    [r.fecha, r.id_operario, id_turno_mysql, r.creado_en],
                )

            for p in MprParte.objects.filter(base_empresa=base).select_related("turno"):
                id_turno_mysql = turno_map.get(p.turno_id)
                if not id_turno_mysql:
                    continue
                uuid_p = str(p.id)
                cursor.execute(
                    """
                    INSERT INTO mpr_parte
                        (uuid_parte, fecha_produccion, id_mpr_turno, id_usuario, registrado_en,
                         notas, movimiento_fisico_ok, id_lista_produccion)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                    ON DUPLICATE KEY UPDATE id_mpr_parte = LAST_INSERT_ID(id_mpr_parte)
                    """,
                    [
                        uuid_p,
                        p.fecha_produccion,
                        id_turno_mysql,
                        p.id_usuario,
                        p.registrado_en,
                        p.notas or "",
                        1 if p.movimiento_fisico_ok else 0,
                        to_int_or_none(p.id_lista_produccion),
                    ],
                )
                parte_map[str(p.id)] = int(cursor.lastrowid)

            for ln in MprParteLinea.objects.filter(parte__base_empresa=base).select_related("parte"):
                id_parte = parte_map.get(str(ln.parte_id))
                if not id_parte:
                    continue
                cursor.execute(
                    """
                    INSERT INTO mpr_parte_linea
                        (id_mpr_parte, id_articulo, id_operario, operario_nombre, cantidad)
                    VALUES (%s, %s, %s, %s, %s)
                    ON DUPLICATE KEY UPDATE cantidad = VALUES(cantidad)
                    """,
                    [
                        id_parte,
                        ln.id_articulo,
                        ln.id_operario,
                        ln.operario_nombre or "-",
                        ln.cantidad,
                    ],
                )

            for aj in MprParteAjuste.objects.filter(parte__base_empresa=base).select_related("parte"):
                id_parte = parte_map.get(str(aj.parte_id))
                if not id_parte:
                    continue
                cursor.execute(
                    """
                    INSERT INTO mpr_parte_ajuste
                        (uuid_ajuste, id_mpr_parte, id_articulo, id_operario, delta, motivo,
                         id_usuario, registrado_en, ajuste_fisico_ok)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ON DUPLICATE KEY UPDATE id_mpr_parte_ajuste = LAST_INSERT_ID(id_mpr_parte_ajuste)
                    """,
                    [
                        str(aj.id),
                        id_parte,
                        aj.id_articulo,
                        aj.id_operario,
                        aj.delta,
                        aj.motivo,
                        aj.id_usuario,
                        aj.registrado_en,
                        1 if aj.ajuste_fisico_ok else 0,
                    ],
                )

            for tl in MprTransicionLote.objects.filter(base_empresa=base):
                cursor.execute(
                    """
                    INSERT INTO mpr_transicion_lote
                        (id_articulo, tipo_origen, tipo_destino, cantidad, codigo_movimiento,
                         id_usuario, creado_en)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                    """,
                    [
                        tl.id_articulo,
                        tl.tipo_origen,
                        tl.tipo_destino,
                        tl.cantidad,
                        to_int_or_none(tl.codigo_movimiento),
                        tl.id_usuario,
                        tl.creado_en,
                    ],
                )

            for lote in MprArmadoLote.objects.filter(base_empresa=base):
                uuid_l = str(lote.id)
                cursor.execute(
                    """
                    INSERT INTO mpr_armado_lote
                        (uuid_lote, modo, id_operario, id_usuario, deposito_origen, deposito_destino,
                         ejecutado_en, cantidad_items, cantidad_exitosos, cantidad_fallidos)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ON DUPLICATE KEY UPDATE id_mpr_armado_lote = LAST_INSERT_ID(id_mpr_armado_lote)
                    """,
                    [
                        uuid_l,
                        lote.modo,
                        to_int_or_none(lote.id_operario),
                        lote.id_usuario,
                        lote.deposito_origen,
                        lote.deposito_destino,
                        lote.ejecutado_en,
                        lote.cantidad_items,
                        lote.cantidad_exitosos,
                        lote.cantidad_fallidos,
                    ],
                )
                lote_map[str(lote.id)] = int(cursor.lastrowid)

            mov_map: dict = {}
            for mov in MprArmadoSurtidoMovimiento.objects.filter(base_empresa=base):
                id_lote = None
                if mov.id_lote_armado_id:
                    id_lote = lote_map.get(str(mov.id_lote_armado_id))
                cursor.execute(
                    """
                    INSERT INTO mpr_armado_surtido_movimiento
                        (codigo_movimiento, id_articulo_pack, cantidad_packs, deposito_origen,
                         deposito_destino, id_lista_produccion, id_mpr_armado_lote, modo,
                         estado_imputacion, id_operario, id_usuario, detalle, creado_en)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """,
                    [
                        mov.codigo_movimiento,
                        mov.id_articulo_pack,
                        mov.cantidad_packs,
                        mov.deposito_origen,
                        mov.deposito_destino,
                        to_int_or_none(mov.id_lista_produccion),
                        id_lote,
                        mov.modo,
                        mov.estado_imputacion,
                        to_int_or_none(mov.id_operario),
                        mov.id_usuario,
                        mov.detalle or "",
                        mov.creado_en,
                    ],
                )
                mov_map[mov.id] = int(cursor.lastrowid)

            for ln in MprArmadoSurtidoLinea.objects.filter(movimiento__base_empresa=base):
                id_mov = mov_map.get(ln.movimiento_id)
                if not id_mov:
                    continue
                cursor.execute(
                    """
                    INSERT INTO mpr_armado_surtido_linea
                        (id_mpr_armado_surtido_movimiento, id_articulo_componente, codigo_articulo,
                         descripcion_articulo, cantidad_por_pack, cantidad_total)
                    VALUES (%s, %s, %s, %s, %s, %s)
                    """,
                    [
                        id_mov,
                        ln.id_articulo_componente,
                        ln.codigo_articulo or "-",
                        ln.descripcion_articulo or "-",
                        ln.cantidad_por_pack,
                        ln.cantidad_total,
                    ],
                )

            for imp in MprImputacionArmado.objects.filter(base_empresa=base):
                cursor.execute(
                    """
                    INSERT INTO mpr_imputacion_armado
                        (codigo_movimiento, id_articulo_pack, cantidad, codigo_movimiento_pedido,
                         id_lista_detalle, origen_regla, id_usuario_supervisor, imputado_en, notas)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """,
                    [
                        imp.codigo_movimiento,
                        imp.id_articulo_pack,
                        imp.cantidad,
                        imp.codigo_movimiento_pedido,
                        to_int_or_none(imp.id_lista_detalle),
                        imp.origen_regla,
                        imp.id_usuario_supervisor,
                        imp.imputado_en,
                        imp.notas or "",
                    ],
                )

            for ep in MprEnvioProduccion.objects.filter(base_empresa=base):
                cursor.execute(
                    """
                    INSERT INTO mpr_envio_produccion
                        (id_articulo, cantidad, id_usuario, anulado, codigo_movimiento_mstock, creado_en)
                    VALUES (%s, %s, %s, %s, %s, %s)
                    """,
                    [
                        ep.id_articulo,
                        ep.cantidad,
                        ep.id_usuario,
                        1 if ep.anulado else 0,
                        to_int_or_none(ep.codigo_movimiento_mstock),
                        ep.creado_en,
                    ],
                )

            cfg = MprEmpresaConfig.objects.filter(base_empresa=base).first()
            if cfg:
                cursor.execute("SELECT COUNT(*) FROM mpr_config")
                if (cursor.fetchone() or [0])[0]:
                    cursor.execute(
                        """
                        UPDATE mpr_config
                        SET bloquear_parte_supera_fabricando = %s
                        ORDER BY id_mpr_config LIMIT 1
                        """,
                        [1 if cfg.bloquear_parte_supera_fabricando else 0],
                    )
                else:
                    cursor.execute(
                        """
                        INSERT INTO mpr_config (bloquear_parte_supera_fabricando)
                        VALUES (%s)
                        """,
                        [1 if cfg.bloquear_parte_supera_fabricando else 0],
                    )

        self.stdout.write(self.style.SUCCESS(f"Migración completada hacia MySQL ({base})."))
