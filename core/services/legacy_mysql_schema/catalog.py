# -*- coding: utf-8 -*-
"""
Catálogo único de migraciones de esquema MySQL (bases AdministraNET / VB6).

**Importante:** cualquier nuevo campo o ALTER requerido por Synap debe añadirse aquí
(ver `.cursorrules` y `docs/general/HERRAMIENTA_GLOBAL_MIGRACION_ESQUEMA_MYSQL.md`).

Las funciones reciben una conexión MySQL del pool (``get_connection``) y hacen ``commit``
cuando aplican cambios.
"""

from __future__ import annotations

import logging
import time
from pathlib import Path
from typing import Any, Callable, Dict, List, Tuple

from .helpers import (
    columna_existe,
    columna_primary_key,
    es_nombre_logico_id_lista_detalle,
    fk_existe,
    indice_existe,
    mensaje_final,
    nombre_tabla_real,
    resultado_vacio,
)

logger = logging.getLogger(__name__)


def _append_migration(
    applied: List[str],
    failed: List[str],
    ok: bool,
    descripcion: str,
    err: str = "",
) -> None:
    if ok:
        applied.append(descripcion)
    else:
        failed.append(f"{descripcion}: {err}" if err else descripcion)


# ---------------------------------------------------------------------------
# Tienda Nube ↔ AdministraNET (columnas de vínculo en tablas legacy)
# ---------------------------------------------------------------------------


def run_tiendanube_integration_mysql(conn) -> Dict[str, Any]:
    """
    Columnas de integración Tiendanube en tablas legacy compartidas con VB6.

    - ``cliente.id_tiendanube``, ``articulo.id_tiendanube``
    - ``comp_ped.id_tiendanube`` (vínculo pedido ↔ orden TN)
    """
    applied: List[str] = []
    failed: List[str] = []
    cursor = conn.cursor()
    try:
        if not columna_existe(cursor, "cliente", "id_tiendanube"):
            cursor.execute(
                'ALTER TABLE cliente ADD COLUMN id_tiendanube BIGINT NULL COMMENT "ID del cliente en Tiendanube"'
            )
            _append_migration(applied, failed, True, "cliente.id_tiendanube")
        if not columna_existe(cursor, "articulo", "id_tiendanube"):
            cursor.execute(
                'ALTER TABLE articulo ADD COLUMN id_tiendanube BIGINT NULL COMMENT "ID del producto en Tiendanube"'
            )
            _append_migration(applied, failed, True, "articulo.id_tiendanube")
        if not columna_existe(cursor, "comp_ped", "id_tiendanube"):
            cursor.execute(
                'ALTER TABLE comp_ped ADD COLUMN id_tiendanube BIGINT NULL '
                'COMMENT "ID de la orden en Tiendanube"'
            )
            _append_migration(applied, failed, True, "comp_ped.id_tiendanube")
        conn.commit()
    except Exception as e:
        conn.rollback()
        logger.exception("run_tiendanube_integration_mysql: %s", e)
        failed.append(str(e))
    finally:
        cursor.close()

    msg = mensaje_final(applied, failed)
    return {
        "success": len(failed) == 0,
        "message": msg,
        "migrations_applied": applied,
        "migrations_failed": failed,
    }


# ---------------------------------------------------------------------------
# MPR — deposito.suma_stock, deposito.tipo_mpr, articulo.stock_reserva
# (docs/mpr/SCHEMA_MPR_ADMINISTRANET92.md, docs/mpr/sql/ALTER_deposito_tipo_mpr.sql)
# ---------------------------------------------------------------------------


def run_mpr_deposito_articulo_mysql(conn) -> Dict[str, Any]:
    applied: List[str] = []
    failed: List[str] = []
    cursor = conn.cursor()
    try:
        tbl_dep = nombre_tabla_real(cursor, "deposito")
        if tbl_dep:
            tdep = tbl_dep.replace("`", "``")
            if not columna_existe(cursor, tbl_dep, "suma_stock"):
                cursor.execute(
                    "ALTER TABLE `{}` ADD COLUMN suma_stock VARCHAR(2) DEFAULT 'Si'".format(tdep)
                )
                _append_migration(applied, failed, True, f"{tbl_dep}.suma_stock")
            if not columna_existe(cursor, tbl_dep, "tipo_mpr"):
                cursor.execute(
                    "ALTER TABLE `{}` ADD COLUMN tipo_mpr VARCHAR(20) NULL "
                    "COMMENT 'Uso MPR: Produccion, SemiElaborado, Terminado, Scrap, 2daSeleccion'".format(
                        tdep
                    )
                )
                _append_migration(applied, failed, True, f"{tbl_dep}.tipo_mpr")

        tbl_art = nombre_tabla_real(cursor, "articulo")
        if tbl_art and not columna_existe(cursor, tbl_art, "stock_reserva"):
            cursor.execute(
                "ALTER TABLE `{}` ADD COLUMN stock_reserva DECIMAL(15,2) DEFAULT NULL".format(
                    tbl_art.replace("`", "``")
                )
            )
            _append_migration(applied, failed, True, f"{tbl_art}.stock_reserva")
        conn.commit()
    except Exception as e:
        conn.rollback()
        logger.exception("run_mpr_deposito_articulo_mysql: %s", e)
        failed.append(str(e))
    finally:
        cursor.close()

    return {
        "success": len(failed) == 0,
        "message": mensaje_final(applied, failed),
        "migrations_applied": applied,
        "migrations_failed": failed,
    }


# ---------------------------------------------------------------------------
# MPR — tabla lista_produccion_agrupada (creación + columnas Synap)
# (docs/mpr/SCHEMA_MPR_ADMINISTRANET92.md, docs/mpr/sql/alter_lista_produccion_agrupada_*.sql)
# ---------------------------------------------------------------------------


def run_mpr_lista_produccion_agrupada_mysql(conn) -> Dict[str, Any]:
    """
    Garantiza la existencia de ``lista_produccion_agrupada`` y columnas usadas por MPR/Synap.

    - Si no existe la tabla ``articulo`` (catálogo AdministraNET), no se puede continuar:
      Synap no crea esa tabla desde aquí.
    - Si no existe ``lista_produccion_agrupada``, la crea con estructura alineada a administranet92.
    - Si ya existe, añade columnas opcionales que falten (OPT, OPA, fecha objetivo, etc.).
    """
    applied: List[str] = []
    failed: List[str] = []
    cursor = conn.cursor()
    try:
        tbl_art = nombre_tabla_real(cursor, "articulo")
        if not tbl_art:
            msg = (
                "No existe la tabla «articulo» (catálogo base AdministraNET). "
                "Synap no puede crearla desde esta herramienta; use una base de empresa con datos ERP."
            )
            return {
                "success": False,
                "message": msg,
                "migrations_applied": [],
                "migrations_failed": [msg],
            }

        tbl_lpa = nombre_tabla_real(cursor, "lista_produccion_agrupada")
        if not tbl_lpa:
            cursor.execute(
                """
                CREATE TABLE lista_produccion_agrupada (
                    id_lista_produccion BIGINT NOT NULL AUTO_INCREMENT,
                    id_articulo BIGINT NOT NULL COMMENT 'articulo.IDArt',
                    cantidad_pedida DOUBLE(15,2) NOT NULL DEFAULT 0,
                    cantidad_pendiente_prod DOUBLE(15,2) NOT NULL DEFAULT 0,
                    cantidad_fabricada_acumulada DOUBLE NULL DEFAULT 0 COMMENT 'Acumulado OPA / armado',
                    cantidad_asignada_opt INT NULL DEFAULT NULL COMMENT 'Cantidad asignada al crear OPT',
                    id_usuario INT NULL DEFAULT NULL,
                    en_proceso_produccion VARCHAR(2) NOT NULL DEFAULT 'No',
                    fecha_objetivo DATE NULL DEFAULT NULL,
                    id_deposito_produccion INT NULL DEFAULT NULL,
                    prioridad INT NULL DEFAULT NULL,
                    id_opt BIGINT NULL DEFAULT NULL,
                    codigo_movimiento_opt INT NULL DEFAULT NULL COMMENT 'Negativo placeholder hasta liberar OPT',
                    id_operario_opt INT NULL DEFAULT NULL COMMENT 'sue_abm_empleado',
                    PRIMARY KEY (id_lista_produccion),
                    KEY idx_lpa_id_articulo (id_articulo),
                    KEY idx_lpa_en_proceso (en_proceso_produccion)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
                COMMENT='Demanda de producción agrupada por artículo (MPR/Synap)'
                """
            )
            _append_migration(applied, failed, True, "CREATE TABLE lista_produccion_agrupada")
            tbl_lpa = nombre_tabla_real(cursor, "lista_produccion_agrupada") or "lista_produccion_agrupada"
        else:
            tbl_lpa = tbl_lpa

        tq = tbl_lpa.replace("`", "``")

        def add_col(name: str, ddl: str) -> None:
            if not columna_existe(cursor, tbl_lpa, name):
                cursor.execute("ALTER TABLE `{}` ADD COLUMN {} {}".format(tq, name, ddl))
                _append_migration(applied, failed, True, f"{tbl_lpa}.{name}")

        # Columnas documentadas en SCHEMA_MPR y scripts sql/ (idempotentes)
        add_col("cantidad_fabricada_acumulada", "DOUBLE NULL DEFAULT 0 COMMENT 'Acumulado OPA'")
        add_col("cantidad_asignada_opt", "INT NULL DEFAULT NULL")
        add_col("fecha_objetivo", "DATE NULL DEFAULT NULL")
        add_col("id_deposito_produccion", "INT NULL DEFAULT NULL")
        add_col("prioridad", "INT NULL DEFAULT NULL")
        add_col("id_opt", "BIGINT NULL DEFAULT NULL")
        add_col("codigo_movimiento_opt", "INT NULL DEFAULT NULL")
        add_col("id_operario_opt", "INT NULL DEFAULT NULL")

        conn.commit()
    except Exception as e:
        conn.rollback()
        logger.exception("run_mpr_lista_produccion_agrupada_mysql: %s", e)
        failed.append(str(e))
    finally:
        cursor.close()

    return {
        "success": len(failed) == 0,
        "message": mensaje_final(applied, failed),
        "migrations_applied": applied,
        "migrations_failed": failed,
    }


# ---------------------------------------------------------------------------
# MPR — tabla lista_produccion_detalle (creación + columnas Synap)
# (docs/mpr/SCHEMA_MPR_ADMINISTRANET92.md §2.6, actualizar_pedidos_produccion en mpr/services.py)
# ---------------------------------------------------------------------------


def _mpr_drop_fk_detalle_codigo_pedido_a_comp_ped_si_existe(cursor, tbl_detalle: str) -> List[str]:
    """
    Si existe una FK desde lista_produccion_detalle.codigo_movimiento_pedido hacia comp_ped,
    la elimina: Synap usa codigo_movimiento_pedido = 0 para demanda por reserva (no hay fila en comp_ped).

    Idempotente; no falla si no hay FK o si information_schema no devuelve coincidencias.
    """
    applied: List[str] = []
    tbl_cp = nombre_tabla_real(cursor, "comp_ped")
    if not tbl_detalle or not tbl_cp:
        return applied
    tq = tbl_detalle.replace("`", "``")
    try:
        cursor.execute(
            """
            SELECT DISTINCT kcu.CONSTRAINT_NAME
            FROM information_schema.KEY_COLUMN_USAGE kcu
            WHERE kcu.TABLE_SCHEMA = DATABASE()
              AND kcu.TABLE_NAME = %s
              AND kcu.COLUMN_NAME = 'codigo_movimiento_pedido'
              AND kcu.REFERENCED_TABLE_SCHEMA = DATABASE()
              AND LOWER(kcu.REFERENCED_TABLE_NAME) = LOWER(%s)
            """,
            (tbl_detalle, tbl_cp),
        )
        for fk_row in cursor.fetchall() or []:
            fk_name = (fk_row[0] or "").strip() if fk_row and fk_row[0] else ""
            if not fk_name:
                continue
            fn = fk_name.replace("`", "``")
            cursor.execute("ALTER TABLE `{}` DROP FOREIGN KEY `{}`".format(tq, fn))
            applied.append(f"DROP FOREIGN KEY `{fk_name}` en {tbl_detalle} (codigo_movimiento_pedido → {tbl_cp})")
    except Exception as e:
        logger.warning("_mpr_drop_fk_detalle_codigo_pedido_a_comp_ped_si_existe: %s", e)
    return applied


def run_mpr_lista_produccion_detalle_mysql(conn) -> Dict[str, Any]:
    """
    Garantiza la existencia de ``lista_produccion_detalle`` para «Actualizar» pedidos y la ventana Pack.

    Requiere ``articulo`` y ``lista_produccion_agrupada`` (ejecutar antes el proveedor
    ``mpr_lista_produccion_agrupada`` si hace falta). La FK explícita hacia agrupada la añade
    el proveedor ``mpr_lista_produccion_trazabilidad`` si aún no existe.
    """
    applied: List[str] = []
    failed: List[str] = []
    cursor = conn.cursor()
    try:
        tbl_art = nombre_tabla_real(cursor, "articulo")
        tbl_agr = nombre_tabla_real(cursor, "lista_produccion_agrupada")
        if not tbl_art:
            msg = (
                "No existe la tabla «articulo». Synap no puede crearla desde esta herramienta."
            )
            return {
                "success": False,
                "message": msg,
                "migrations_applied": [],
                "migrations_failed": [msg],
            }
        if not tbl_agr:
            msg = (
                "No existe «lista_produccion_agrupada». Ejecute antes el proveedor "
                "«MPR — tabla lista_produccion_agrupada» y vuelva a intentar."
            )
            return {
                "success": False,
                "message": msg,
                "migrations_applied": [],
                "migrations_failed": [msg],
            }

        tbl_det = nombre_tabla_real(cursor, "lista_produccion_detalle")
        if not tbl_det:
            cursor.execute(
                """
                CREATE TABLE lista_produccion_detalle (
                    id_lista_detalle BIGINT NOT NULL AUTO_INCREMENT,
                    id_lista_produccion BIGINT NULL DEFAULT NULL COMMENT 'lista_produccion_agrupada.id_lista_produccion',
                    codigo_movimiento_pedido INT NOT NULL COMMENT 'comp_ped.CodigoMovimiento; 0 = demanda sintética por reserva',
                    id_articulo INT NOT NULL COMMENT 'articulo.IDArt',
                    cantidad_pedida DOUBLE(15,2) NOT NULL DEFAULT 0,
                    cantidad_pendiente_prod DOUBLE(15,2) NOT NULL DEFAULT 0,
                    origen_demanda VARCHAR(16) NULL DEFAULT NULL COMMENT 'PEDIDO|RESERVA',
                    id_usuario INT NULL DEFAULT NULL,
                    en_proceso_produccion VARCHAR(2) NOT NULL DEFAULT 'No',
                    Fecha DATE NULL DEFAULT NULL,
                    id_operario_opt INT NULL DEFAULT NULL COMMENT 'sue_abm_empleado',
                    PRIMARY KEY (id_lista_detalle),
                    KEY idx_lpd_ped_art (codigo_movimiento_pedido, id_articulo),
                    KEY idx_lpd_id_lista_prod (id_lista_produccion)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
                COMMENT='Detalle pedido–artículo para producción (MPR/Synap)'
                """
            )
            _append_migration(applied, failed, True, "CREATE TABLE lista_produccion_detalle")
        else:
            tq = tbl_det.replace("`", "``")
            for name, ddl in (
                ("id_lista_produccion", "BIGINT NULL DEFAULT NULL"),
                ("Fecha", "DATE NULL DEFAULT NULL"),
                ("id_usuario", "INT NULL DEFAULT NULL"),
                ("id_operario_opt", "INT NULL DEFAULT NULL"),
                ("origen_demanda", "VARCHAR(16) NULL DEFAULT NULL COMMENT 'PEDIDO|RESERVA'"),
            ):
                if not columna_existe(cursor, tbl_det, name):
                    cursor.execute("ALTER TABLE `{}` ADD COLUMN {} {}".format(tq, name, ddl))
                    _append_migration(applied, failed, True, f"{tbl_det}.{name}")
            for msg in _mpr_drop_fk_detalle_codigo_pedido_a_comp_ped_si_existe(cursor, tbl_det):
                _append_migration(applied, failed, True, msg)

        conn.commit()
    except Exception as e:
        conn.rollback()
        logger.exception("run_mpr_lista_produccion_detalle_mysql: %s", e)
        failed.append(str(e))
    finally:
        cursor.close()

    return {
        "success": len(failed) == 0,
        "message": mensaje_final(applied, failed),
        "migrations_applied": applied,
        "migrations_failed": failed,
    }


# ---------------------------------------------------------------------------
# MPR — trazabilidad lista_produccion_detalle
# (docs/mpr/sql/alter_lista_produccion_detalle_trazabilidad.sql)
# ---------------------------------------------------------------------------


def run_mpr_lista_produccion_detalle_trazabilidad_mysql(conn) -> Dict[str, Any]:
    """
    Ajusta columnas y FK en ``lista_produccion_detalle`` respecto de
    ``lista_produccion_agrupada``. Puede ser destructivo si hay datos inconsistentes;
    en entornos reales ejecutar con backup y ventana de mantenimiento.
    """
    applied: List[str] = []
    failed: List[str] = []
    cursor = conn.cursor()
    try:
        tbl_detalle = nombre_tabla_real(cursor, "lista_produccion_detalle")
        tbl_agrupada = nombre_tabla_real(cursor, "lista_produccion_agrupada")
        if not tbl_detalle or not tbl_agrupada:
            msg = "Faltan tablas lista_produccion_detalle o lista_produccion_agrupada; omitido."
            cursor.close()
            return {
                "success": True,
                "message": msg,
                "migrations_applied": [],
                "migrations_failed": [],
            }

        tiene_id_lista_produccion = columna_existe(cursor, tbl_detalle, "id_lista_produccion")
        tiene_id_lista_detalle = columna_existe(cursor, tbl_detalle, "id_lista_detalle")
        logger.info(
            "MPR trazabilidad detalle: inicio tabla=%s agrupada=%s id_lista_produccion=%s id_lista_detalle=%s",
            tbl_detalle,
            tbl_agrupada,
            tiene_id_lista_produccion,
            tiene_id_lista_detalle,
        )

        conn.autocommit(False)
        try:
            if tiene_id_lista_produccion and not tiene_id_lista_detalle:
                cursor.execute(
                    "SELECT CONSTRAINT_NAME FROM information_schema.KEY_COLUMN_USAGE "
                    "WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = %s AND COLUMN_NAME = 'id_lista_produccion' "
                    "AND REFERENCED_TABLE_NAME IS NOT NULL LIMIT 1",
                    (tbl_detalle,),
                )
                row = cursor.fetchone()
                fk_name = (row[0] if row and row[0] else "").strip() if row else None
                if fk_name:
                    logger.info(
                        "MPR trazabilidad detalle: ejecutando DROP FOREIGN KEY %s en %s (puede esperar bloqueos MDL)",
                        fk_name,
                        tbl_detalle,
                    )
                    cursor.execute(
                        "ALTER TABLE `{}` DROP FOREIGN KEY `{}`".format(
                            tbl_detalle.replace("`", "``"), fk_name.replace("`", "``")
                        )
                    )
                    applied.append("DROP FK id_lista_produccion en detalle")
                logger.info(
                    "MPR trazabilidad detalle: ejecutando CHANGE COLUMN id_lista_produccion → id_lista_detalle en %s "
                    "(operación larga en tablas grandes; sin error en log = aún en curso o esperando bloqueo)",
                    tbl_detalle,
                )
                cursor.execute(
                    "ALTER TABLE `{}` CHANGE COLUMN id_lista_produccion id_lista_detalle BIGINT NOT NULL AUTO_INCREMENT".format(
                        tbl_detalle.replace("`", "``")
                    )
                )
                applied.append("Renombrar id_lista_produccion → id_lista_detalle")
                tiene_id_lista_produccion = False

            if not columna_existe(cursor, tbl_detalle, "id_lista_produccion"):
                after_clause = (
                    " AFTER id_lista_detalle" if columna_existe(cursor, tbl_detalle, "id_lista_detalle") else ""
                )
                logger.info("MPR trazabilidad detalle: ADD COLUMN id_lista_produccion en %s", tbl_detalle)
                cursor.execute(
                    "ALTER TABLE `{}` ADD COLUMN id_lista_produccion BIGINT NULL DEFAULT NULL{}".format(
                        tbl_detalle.replace("`", "``"), after_clause
                    )
                )
                applied.append("Añadir id_lista_produccion en detalle")

            fk_name = "fk_detalle_agrupada_lista_produccion"
            if not fk_existe(cursor, tbl_detalle, fk_name):
                logger.info("MPR trazabilidad detalle: ADD CONSTRAINT %s en %s", fk_name, tbl_detalle)
                cursor.execute(
                    "ALTER TABLE `{det}` ADD CONSTRAINT `{fk}` FOREIGN KEY (id_lista_produccion) "
                    "REFERENCES `{agr}`(id_lista_produccion)".format(
                        det=tbl_detalle.replace("`", "``"),
                        fk=fk_name,
                        agr=tbl_agrupada.replace("`", "``"),
                    )
                )
                applied.append("FK " + fk_name)

            idx_name = "idx_detalle_id_lista_produccion"
            if not indice_existe(cursor, tbl_detalle, idx_name):
                logger.info("MPR trazabilidad detalle: CREATE INDEX %s en %s", idx_name, tbl_detalle)
                cursor.execute(
                    "CREATE INDEX `{}` ON `{}`(id_lista_produccion)".format(
                        idx_name, tbl_detalle.replace("`", "``")
                    )
                )
                applied.append("Índice " + idx_name)

            conn.commit()
        except Exception as inner:
            conn.rollback()
            raise inner
    except Exception as e:
        logger.exception("run_mpr_lista_produccion_detalle_trazabilidad_mysql: %s", e)
        failed.append(str(e))
    finally:
        conn.autocommit(True)
        cursor.close()

    logger.info(
        "MPR trazabilidad detalle: fin success=%s applied=%s failed=%s",
        len(failed) == 0,
        applied,
        failed,
    )
    return {
        "success": len(failed) == 0,
        "message": mensaje_final(applied, failed),
        "migrations_applied": applied,
        "migrations_failed": failed,
    }


# ---------------------------------------------------------------------------
# Objetivos de venta (Synap → tabla legacy por cliente / período)
# ---------------------------------------------------------------------------


def run_viajantes_objetivos_ventas_mysql(conn) -> Dict[str, Any]:
    """
    Crea ``viajantes_objetivos_ventas`` y ``viajantes_objetivos_periodo`` si no existen,
    y añade ``id_periodo`` en el detalle cuando falte (cabecera de intervalo + anulado Si/No).

    Ver docs/general/tablas/viajantes_objetivos_ventas.md y docs/reports/SPEC_INFORME_OBJETIVOS_VENTAS_BO.md.
    """
    applied: List[str] = []
    failed: List[str] = []
    cursor = conn.cursor()
    try:
        cursor.execute(
            """
            SELECT COUNT(*) FROM information_schema.tables
            WHERE table_schema = DATABASE() AND table_name = 'viajantes_objetivos_ventas'
            """
        )
        row = cursor.fetchone()
        exists = row and int(row[0] or 0) > 0
        if not exists:
            cursor.execute(
                """
                CREATE TABLE viajantes_objetivos_ventas (
                    id BIGINT NOT NULL AUTO_INCREMENT,
                    Codigo INT NOT NULL COMMENT 'cliente.Codigo',
                    CodViajante INT NOT NULL COMMENT 'Snapshot viajante al guardar',
                    id_periodo BIGINT NULL COMMENT 'viajantes_objetivos_periodo.id',
                    fecha_desde DATE NOT NULL,
                    fecha_hasta DATE NOT NULL,
                    objetivo DECIMAL(15, 2) NOT NULL DEFAULT 0.00,
                    PRIMARY KEY (id),
                    INDEX idx_vov_cliente (Codigo),
                    INDEX idx_vov_viajante (CodViajante),
                    INDEX idx_vov_periodo_id (id_periodo),
                    INDEX idx_vov_periodo (fecha_desde, fecha_hasta)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
                COMMENT='Objetivos de venta por cliente y período (Synap + AdministraNET)'
                """
            )
            _append_migration(applied, failed, True, "CREATE TABLE viajantes_objetivos_ventas")
        else:
            _append_migration(applied, failed, True, "viajantes_objetivos_ventas ya existe (omitido)")

        cursor.execute(
            """
            SELECT COUNT(*) FROM information_schema.tables
            WHERE table_schema = DATABASE() AND table_name = 'viajantes_objetivos_periodo'
            """
        )
        row_p = cursor.fetchone()
        exists_p = row_p and int(row_p[0] or 0) > 0
        if not exists_p:
            cursor.execute(
                """
                CREATE TABLE viajantes_objetivos_periodo (
                    id BIGINT NOT NULL AUTO_INCREMENT,
                    fecha_desde DATE NOT NULL,
                    fecha_hasta DATE NOT NULL,
                    descripcion VARCHAR(120) NOT NULL DEFAULT '-'
                        COMMENT 'Etiqueta del período (ej. mes y año); "-" si no se informa',
                    anulado VARCHAR(3) NOT NULL DEFAULT 'No' COMMENT 'Si / No (paridad AdministraNET)',
                    PRIMARY KEY (id),
                    INDEX idx_vop_fechas (fecha_desde, fecha_hasta),
                    INDEX idx_vop_anulado (anulado)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
                COMMENT='Cabecera de intervalo para objetivos de venta (Synap)'
                """
            )
            _append_migration(applied, failed, True, "CREATE TABLE viajantes_objetivos_periodo")
        else:
            _append_migration(applied, failed, True, "viajantes_objetivos_periodo ya existe (omitido)")

        tbl_vop = nombre_tabla_real(cursor, "viajantes_objetivos_periodo")
        if tbl_vop and not columna_existe(cursor, tbl_vop, "descripcion"):
            cursor.execute(
                """
                ALTER TABLE `{}`
                ADD COLUMN descripcion VARCHAR(120) NOT NULL DEFAULT '-'
                    COMMENT 'Etiqueta del período (ej. mes y año); "-" si no se informa'
                AFTER fecha_hasta
                """.format(
                    tbl_vop.replace("`", "``"),
                )
            )
            _append_migration(applied, failed, True, f"ALTER TABLE {tbl_vop} ADD descripcion")

        tbl_vov = nombre_tabla_real(cursor, "viajantes_objetivos_ventas")
        if tbl_vov and not columna_existe(cursor, tbl_vov, "id_periodo"):
            cursor.execute(
                """
                ALTER TABLE `{}`
                ADD COLUMN id_periodo BIGINT NULL COMMENT 'viajantes_objetivos_periodo.id' AFTER CodViajante
                """.format(
                    tbl_vov.replace("`", "``"),
                )
            )
            _append_migration(applied, failed, True, f"ALTER TABLE {tbl_vov} ADD id_periodo")
            if not indice_existe(cursor, tbl_vov, "idx_vov_periodo_id"):
                cursor.execute(
                    "CREATE INDEX idx_vov_periodo_id ON `{}` (id_periodo)".format(
                        tbl_vov.replace("`", "``"),
                    )
                )
                _append_migration(applied, failed, True, f"CREATE INDEX idx_vov_periodo_id en {tbl_vov}")

        conn.commit()
    except Exception as e:
        conn.rollback()
        logger.exception("run_viajantes_objetivos_ventas_mysql: %s", e)
        failed.append(str(e))
    finally:
        cursor.close()

    return {
        "success": len(failed) == 0,
        "message": mensaje_final(applied, failed),
        "migrations_applied": applied,
        "migrations_failed": failed,
    }


# ---------------------------------------------------------------------------
# Self-checkout (tablas por empresa en MySQL)
# (self_checkout/sql/001_self_checkout_tables.sql; columnas 003/005)
# ---------------------------------------------------------------------------


def _sc_sql_strip_leading_comments(stmt: str) -> str:
    lines = stmt.split("\n")
    for _i, line in enumerate(lines):
        s = line.strip()
        if s and not s.startswith("--"):
            return "\n".join(lines[_i:]).strip()
    return ""


def run_self_checkout_core_tables_mysql(conn) -> Dict[str, Any]:
    """
    Crea las tablas ``self_checkout_*`` (kiosco, carrito, sesión, etc.) si no existen
    y añade columnas que usa la UI (``enviar_factura_email``, ``modo_tpv``, columnas TPV en ítems).

    Equivalente a ``manage.py create_self_checkout_tables`` más alters idempotentes de las migraciones 003 y 005.
    """
    applied: List[str] = []
    failed: List[str] = []
    from django.apps import apps

    try:
        app_path = Path(apps.get_app_config("self_checkout").path)
    except LookupError:
        msg = "La app Django «self_checkout» no está instalada."
        return {
            "success": False,
            "message": msg,
            "migrations_applied": [],
            "migrations_failed": [msg],
        }

    sql_path = app_path / "sql" / "001_self_checkout_tables.sql"
    if not sql_path.is_file():
        msg = f"No se encontró el archivo {sql_path}"
        return {
            "success": False,
            "message": msg,
            "migrations_applied": [],
            "migrations_failed": [msg],
        }

    cursor = conn.cursor()
    try:
        sql_content = sql_path.read_text(encoding="utf-8")
        raw_statements = [s.strip() for s in sql_content.split(";") if s.strip()]
        statements: List[str] = []
        for stmt in raw_statements:
            stmt = _sc_sql_strip_leading_comments(stmt)
            if stmt:
                statements.append(stmt)

        for stmt in statements:
            cursor.execute(stmt)
        _append_migration(applied, failed, True, "DDL self_checkout (001_self_checkout_tables.sql)")

        tk = nombre_tabla_real(cursor, "self_checkout_kiosk")
        if tk:
            tq = tk.replace("`", "``")
            if not columna_existe(cursor, tk, "enviar_factura_email"):
                cursor.execute(
                    "ALTER TABLE `{}` ADD COLUMN enviar_factura_email TINYINT(1) NOT NULL DEFAULT 1 "
                    "COMMENT '1=habilitar solicitud y envío de factura por email'".format(tq)
                )
                _append_migration(applied, failed, True, f"{tk}.enviar_factura_email")
            if not columna_existe(cursor, tk, "modo_tpv"):
                cursor.execute(
                    "ALTER TABLE `{}` ADD COLUMN modo_tpv TINYINT(1) NOT NULL DEFAULT 0 COMMENT '1=TPV'".format(
                        tq
                    )
                )
                _append_migration(applied, failed, True, f"{tk}.modo_tpv")

        tci = nombre_tabla_real(cursor, "self_checkout_cart_item")
        if tci:
            tcq = tci.replace("`", "``")
            for col, ddl in (
                ("codigo_barras", "VARCHAR(64) DEFAULT NULL COMMENT 'Código de barra'"),
                ("porcentaje_descuento", "DECIMAL(8,4) NOT NULL DEFAULT 0 COMMENT '% descuento renglón'"),
                ("promocion", "VARCHAR(255) DEFAULT NULL COMMENT 'Promoción'"),
                ("detalle", "TEXT DEFAULT NULL COMMENT 'Detalle renglón'"),
            ):
                if not columna_existe(cursor, tci, col):
                    cursor.execute("ALTER TABLE `{}` ADD COLUMN {} {}".format(tcq, col, ddl))
                    _append_migration(applied, failed, True, f"{tci}.{col}")

        conn.commit()
    except Exception as e:
        conn.rollback()
        logger.exception("run_self_checkout_core_tables_mysql: %s", e)
        failed.append(str(e))
    finally:
        cursor.close()

    return {
        "success": len(failed) == 0,
        "message": mensaje_final(applied, failed),
        "migrations_applied": applied,
        "migrations_failed": failed,
    }


def run_mpr_lista_produccion_detalle_corregir_pk_nombre_mysql(conn) -> Dict[str, Any]:
    """
    Renombra la PK de ``lista_produccion_detalle`` a ``id_lista_detalle`` cuando el nombre
    físico quedó corrupto (p. ej. ``id\\x1f_lista_detalle``) tras una migración parcial.
    Sin este arreglo, Synap puede confundir ``id_lista_produccion`` (FK) con la PK de fila
    y la sincronización de demanda por reserva pisa las líneas de pedidos PED.
    """
    applied: List[str] = []
    failed: List[str] = []
    cursor = conn.cursor()
    try:
        tbl_detalle = nombre_tabla_real(cursor, "lista_produccion_detalle")
        if not tbl_detalle:
            cursor.close()
            return {
                "success": True,
                "message": "Tabla lista_produccion_detalle no existe; omitido.",
                "migrations_applied": [],
                "migrations_failed": [],
            }

        if columna_existe(cursor, tbl_detalle, "id_lista_detalle"):
            cursor.close()
            return {
                "success": True,
                "message": "Columna id_lista_detalle ya existe; no se requiere corrección.",
                "migrations_applied": [],
                "migrations_failed": [],
            }

        pk_fisica = columna_primary_key(cursor, tbl_detalle)
        if not pk_fisica or not es_nombre_logico_id_lista_detalle(pk_fisica):
            cursor.close()
            return {
                "success": True,
                "message": "No se detectó PK corrupta de id_lista_detalle; omitido.",
                "migrations_applied": [],
                "migrations_failed": [],
            }

        tbl_esc = tbl_detalle.replace("`", "``")
        pk_esc = pk_fisica.replace("`", "``")
        conn.autocommit(False)
        try:
            cursor.execute(
                "ALTER TABLE `{}` CHANGE COLUMN `{}` id_lista_detalle BIGINT NOT NULL AUTO_INCREMENT".format(
                    tbl_esc, pk_esc
                )
            )
            applied.append(
                "Renombrar PK lista_produccion_detalle ({!r} → id_lista_detalle)".format(pk_fisica)
            )
            conn.commit()
        except Exception as inner:
            conn.rollback()
            raise inner
    except Exception as e:
        logger.exception("run_mpr_lista_produccion_detalle_corregir_pk_nombre_mysql: %s", e)
        failed.append(str(e))
    finally:
        conn.autocommit(True)
        cursor.close()

    return {
        "success": len(failed) == 0,
        "message": mensaje_final(applied, failed),
        "migrations_applied": applied,
        "migrations_failed": failed,
    }


# ---------------------------------------------------------------------------
# Asignación vendedor ↔ cliente / marca (Synap ventas + ecom)
# ---------------------------------------------------------------------------

_ECOM_FUENTE_VENDEDOR_CONFIG: Tuple[Dict[str, str], ...] = (
    {
        "key_permiso": "ecom_fuente_vendedor_cliente",
        "nombre_permiso": "Fuente relación vendedor-cliente",
        "detalle_permiso": (
            "legacy: filtra por cliente.CodViajante; "
            "tabla: filtra por vendedores_clientes_asignacion"
        ),
        "grupo_permiso": "Ecom Ventas",
        "tipo_permiso": "Texto",
        "valor_permiso": "legacy",
        "detalle_valor_permiso": "legacy-tabla",
    },
    {
        "key_permiso": "ecom_fuente_vendedor_marca",
        "nombre_permiso": "Fuente relación vendedor-marca",
        "detalle_permiso": (
            "legacy: sin tabla de asignación por marca; "
            "tabla: usa vendedores_marcas_asignacion"
        ),
        "grupo_permiso": "Ecom Ventas",
        "tipo_permiso": "Texto",
        "valor_permiso": "legacy",
        "detalle_valor_permiso": "legacy-tabla",
    },
)


def _tabla_existe(cursor, table_name: str) -> bool:
    cursor.execute(
        """
        SELECT COUNT(*) FROM information_schema.tables
        WHERE table_schema = DATABASE() AND table_name = %s
        """,
        (table_name,),
    )
    row = cursor.fetchone()
    return bool(row and int(row[0] or 0) > 0)


def _ecom_config_key_existe(cursor, tabla: str, key_permiso: str) -> bool:
    if not _tabla_existe(cursor, tabla):
        return False
    tbl = nombre_tabla_real(cursor, tabla) or tabla
    cursor.execute(
        f"SELECT 1 FROM `{tbl.replace('`', '``')}` WHERE key_permiso = %s LIMIT 1",
        (key_permiso,),
    )
    return cursor.fetchone() is not None


def _insertar_ecom_config_si_falta(
    cursor,
    tabla: str,
    row: Dict[str, str],
    applied: List[str],
    failed: List[str],
) -> None:
    key = row["key_permiso"]
    if _ecom_config_key_existe(cursor, tabla, key):
        _append_migration(applied, failed, True, f"{tabla}.{key} ya existe (omitido)")
        return
    tbl = nombre_tabla_real(cursor, tabla) or tabla
    tbl_esc = tbl.replace("`", "``")
    cursor.execute(
        f"""
        INSERT INTO `{tbl_esc}` (
            key_permiso, nombre_permiso, detalle_permiso,
            grupo_permiso, tipo_permiso, valor_permiso, detalle_valor_permiso
        ) VALUES (%s, %s, %s, %s, %s, %s, %s)
        """,
        (
            row["key_permiso"],
            row["nombre_permiso"],
            row["detalle_permiso"],
            row["grupo_permiso"],
            row["tipo_permiso"],
            row["valor_permiso"],
            row["detalle_valor_permiso"],
        ),
    )
    _append_migration(applied, failed, True, f"INSERT {tabla}.{key}")


def run_vendedores_asignacion_mysql(conn) -> Dict[str, Any]:
    """
    Tablas ``vendedores_clientes_asignacion`` y ``vendedores_marcas_asignacion``,
    más claves en ``configuracion_ecom_conf`` / ``configuracion_ecom`` para elegir
    fuente legacy vs tabla en ecom.

    Ver ``docs/general/SPEC_VENDEDOR_ASIGNACION_VENTAS.md``.
    """
    applied: List[str] = []
    failed: List[str] = []
    cursor = conn.cursor()
    try:
        if not _tabla_existe(cursor, "vendedores_clientes_asignacion"):
            cursor.execute(
                """
                CREATE TABLE vendedores_clientes_asignacion (
                    id BIGINT NOT NULL AUTO_INCREMENT,
                    id_vendedor INT NOT NULL COMMENT 'viajantes.CodViajante',
                    id_cliente INT NOT NULL COMMENT 'cliente.Codigo',
                    fecha_alta DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    fecha_mod DATETIME NULL ON UPDATE CURRENT_TIMESTAMP,
                    usuario_mod VARCHAR(60) NULL,
                    PRIMARY KEY (id),
                    UNIQUE KEY uk_vca_cliente (id_cliente),
                    INDEX idx_vca_vendedor (id_vendedor)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
                COMMENT='Asignación vendedor-cliente (Synap; alternativa a cliente.CodViajante)'
                """
            )
            _append_migration(applied, failed, True, "CREATE TABLE vendedores_clientes_asignacion")
        else:
            _append_migration(
                applied, failed, True, "vendedores_clientes_asignacion ya existe (omitido)"
            )

        if not _tabla_existe(cursor, "vendedores_marcas_asignacion"):
            cursor.execute(
                """
                CREATE TABLE vendedores_marcas_asignacion (
                    id BIGINT NOT NULL AUTO_INCREMENT,
                    id_vendedor INT NOT NULL COMMENT 'viajantes.CodViajante',
                    id_marca INT NOT NULL COMMENT 'marca.CodMarca',
                    fecha_alta DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    fecha_mod DATETIME NULL ON UPDATE CURRENT_TIMESTAMP,
                    usuario_mod VARCHAR(60) NULL,
                    PRIMARY KEY (id),
                    UNIQUE KEY uk_vma_marca (id_marca),
                    INDEX idx_vma_vendedor (id_vendedor)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
                COMMENT='Asignación vendedor-marca (Synap)'
                """
            )
            _append_migration(applied, failed, True, "CREATE TABLE vendedores_marcas_asignacion")
        else:
            _append_migration(
                applied, failed, True, "vendedores_marcas_asignacion ya existe (omitido)"
            )

        for row in _ECOM_FUENTE_VENDEDOR_CONFIG:
            _insertar_ecom_config_si_falta(cursor, "configuracion_ecom_conf", row, applied, failed)
            _insertar_ecom_config_si_falta(cursor, "configuracion_ecom", row, applied, failed)

        conn.commit()
    except Exception as e:
        conn.rollback()
        logger.exception("run_vendedores_asignacion_mysql: %s", e)
        failed.append(str(e))
    finally:
        cursor.close()

    return {
        "success": len(failed) == 0,
        "message": mensaje_final(applied, failed),
        "migrations_applied": applied,
        "migrations_failed": failed,
    }


# ---------------------------------------------------------------------------
# Registro para la UI y ejecución selectiva
# ---------------------------------------------------------------------------

ProviderFn = Callable[[Any], Dict[str, Any]]

PROVIDER_REGISTRY: List[Dict[str, Any]] = [
    {
        "id": "tiendanube_integration",
        "title": "Integración Tienda Nube",
        "description": (
            "Columnas id_tiendanube en cliente, articulo y comp_ped para sincronización "
            "con Tienda Nube / Nuvemshop."
        ),
        "risk": "bajo",
        "run": run_tiendanube_integration_mysql,
    },
    {
        "id": "mpr_deposito_articulo",
        "title": "MPR — depósito y artículo",
        "description": (
            "Columnas deposito.suma_stock, deposito.tipo_mpr (configuración por tipo MPR) y "
            "articulo.stock_reserva. Ver docs/mpr/SCHEMA_MPR_ADMINISTRANET92.md y "
            "docs/mpr/sql/ALTER_deposito_tipo_mpr.sql."
        ),
        "risk": "bajo",
        "run": run_mpr_deposito_articulo_mysql,
    },
    {
        "id": "mpr_lista_produccion_agrupada",
        "title": "MPR — tabla lista_produccion_agrupada",
        "description": (
            "Crea la tabla lista_produccion_agrupada si no existe (bases sin MPR previo) y añade "
            "columnas opcionales Synap (OPT, fecha objetivo, cantidad_fabricada_acumulada, etc.). "
            "Requiere que exista la tabla articulo (no se crea aquí). "
            "Ver docs/mpr/SCHEMA_MPR_ADMINISTRANET92.md."
        ),
        "risk": "medio",
        "run": run_mpr_lista_produccion_agrupada_mysql,
    },
    {
        "id": "mpr_lista_produccion_detalle",
        "title": "MPR — tabla lista_produccion_detalle",
        "description": (
            "Crea la tabla lista_produccion_detalle si no existe (demanda por pedido y artículo; "
            "«Actualizar» en MPR). Requiere articulo y lista_produccion_agrupada. "
            "Si la tabla ya existe, solo añade columnas opcionales que falten (Fecha, id_usuario, …). "
            "Elimina una FK heredada detalle.codigo_movimiento_pedido → comp_ped si existe, porque Synap "
            "usa código 0 para demanda por reserva (sin fila en comp_ped). "
            "Después conviene ejecutar «MPR — trazabilidad lista producción (detalle)» para FK/índices hacia agrupada."
        ),
        "risk": "medio",
        "run": run_mpr_lista_produccion_detalle_mysql,
    },
    {
        "id": "mpr_lista_produccion_trazabilidad",
        "title": "MPR — trazabilidad lista producción (detalle)",
        "description": (
            "Ajuste de lista_produccion_detalle e índices/FK hacia lista_produccion_agrupada. "
            "Ejecutar con precaución si hay datos en esas tablas."
        ),
        "risk": "medio",
        "run": run_mpr_lista_produccion_detalle_trazabilidad_mysql,
    },
    {
        "id": "mpr_lista_produccion_detalle_pk_nombre",
        "title": "MPR — corregir nombre PK lista_produccion_detalle",
        "description": (
            "Renombra la columna PRIMARY KEY corrupta (p. ej. id\\x1f_lista_detalle) a "
            "id_lista_detalle. Ejecutar si la demanda por reserva pisa cantidades de pedidos PED "
            "en ventana-pack. Complementa «MPR — trazabilidad lista producción (detalle)»."
        ),
        "risk": "bajo",
        "run": run_mpr_lista_produccion_detalle_corregir_pk_nombre_mysql,
    },
    {
        "id": "self_checkout_core_tables",
        "title": "Self-checkout — tablas MySQL (kiosco, carrito, sesión)",
        "description": (
            "Crea las tablas self_checkout_* en la base de la empresa (``001_self_checkout_tables.sql``) "
            "y columnas posteriores necesarias para el alta de kioscos y TPV (enviar_factura_email, modo_tpv, "
            "columnas en ítems de carrito). Equivale a ``create_self_checkout_tables`` + alters 003/005. "
            "Ver self_checkout/README.md."
        ),
        "risk": "bajo",
        "run": run_self_checkout_core_tables_mysql,
    },
    {
        "id": "viajantes_objetivos_ventas",
        "title": "Objetivos de venta (cabecera + detalle)",
        "description": (
            "Tablas ``viajantes_objetivos_periodo`` (intervalo y anulado Si/No) y "
            "``viajantes_objetivos_ventas`` (detalle por cliente; ``id_periodo`` opcional en datos heredados)."
        ),
        "risk": "bajo",
        "run": run_viajantes_objetivos_ventas_mysql,
    },
    {
        "id": "vendedores_asignacion",
        "title": "Ventas — asignación vendedor-cliente / vendedor-marca",
        "description": (
            "Tablas ``vendedores_clientes_asignacion`` y ``vendedores_marcas_asignacion``, "
            "y claves ``ecom_fuente_vendedor_cliente`` / ``ecom_fuente_vendedor_marca`` "
            "(legacy | tabla) en configuracion_ecom_conf y configuracion_ecom."
        ),
        "risk": "bajo",
        "run": run_vendedores_asignacion_mysql,
    },
]


def run_provider_by_id(provider_id: str, conn) -> Dict[str, Any]:
    for p in PROVIDER_REGISTRY:
        if p["id"] == provider_id:
            t0 = time.monotonic()
            logger.info(
                "legacy_mysql_schema: inicio proveedor id=%s title=%s",
                p["id"],
                p.get("title"),
            )
            r = p["run"](conn)
            logger.info(
                "legacy_mysql_schema: fin proveedor id=%s success=%s duracion_s=%.2f",
                p["id"],
                r.get("success"),
                time.monotonic() - t0,
            )
            return r
    return {
        "success": False,
        "message": f"Proveedor desconocido: {provider_id}",
        "migrations_applied": [],
        "migrations_failed": [f"unknown:{provider_id}"],
    }


def run_all_providers(conn) -> Dict[str, Any]:
    """Ejecuta todos los proveedores en orden; acumula resultados."""
    all_applied: List[str] = []
    all_failed: List[str] = []
    overall_ok = True
    messages: List[str] = []
    t_all = time.monotonic()
    logger.info(
        "legacy_mysql_schema: inicio run_all (%s proveedores)",
        len(PROVIDER_REGISTRY),
    )

    for p in PROVIDER_REGISTRY:
        t0 = time.monotonic()
        logger.info(
            "legacy_mysql_schema: inicio proveedor id=%s title=%s",
            p["id"],
            p.get("title"),
        )
        r = p["run"](conn)
        logger.info(
            "legacy_mysql_schema: fin proveedor id=%s success=%s duracion_s=%.2f",
            p["id"],
            r.get("success"),
            time.monotonic() - t0,
        )
        all_applied.extend(r.get("migrations_applied") or [])
        all_failed.extend(r.get("migrations_failed") or [])
        if r.get("message"):
            messages.append(f"[{p['id']}] {r['message']}")
        if not r.get("success", True):
            overall_ok = False

    logger.info(
        "legacy_mysql_schema: fin run_all duracion_total_s=%.2f",
        time.monotonic() - t_all,
    )
    return {
        "success": overall_ok and len(all_failed) == 0,
        "message": "\n".join(messages) if messages else mensaje_final(all_applied, all_failed),
        "migrations_applied": all_applied,
        "migrations_failed": all_failed,
    }
