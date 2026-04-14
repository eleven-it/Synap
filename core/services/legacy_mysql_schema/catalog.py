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
from typing import Any, Callable, Dict, List, Tuple

from .helpers import (
    columna_existe,
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
    Añade columnas ``id_tiendanube`` en ``cliente`` y ``articulo`` si no existen.
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
# MPR — deposito.suma_stock, articulo.stock_reserva
# (docs/mpr/SCHEMA_MPR_ADMINISTRANET92.md)
# ---------------------------------------------------------------------------


def run_mpr_deposito_articulo_mysql(conn) -> Dict[str, Any]:
    applied: List[str] = []
    failed: List[str] = []
    cursor = conn.cursor()
    try:
        if not columna_existe(cursor, "deposito", "suma_stock"):
            cursor.execute(
                "ALTER TABLE deposito ADD COLUMN suma_stock VARCHAR(2) DEFAULT 'Si'"
            )
            _append_migration(applied, failed, True, "deposito.suma_stock")
        if not columna_existe(cursor, "articulo", "stock_reserva"):
            cursor.execute(
                "ALTER TABLE articulo ADD COLUMN stock_reserva DECIMAL(15,2) DEFAULT NULL"
            )
            _append_migration(applied, failed, True, "articulo.stock_reserva")
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
                    cursor.execute(
                        "ALTER TABLE `{}` DROP FOREIGN KEY `{}`".format(
                            tbl_detalle.replace("`", "``"), fk_name.replace("`", "``")
                        )
                    )
                    applied.append("DROP FK id_lista_produccion en detalle")
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
                cursor.execute(
                    "ALTER TABLE `{}` ADD COLUMN id_lista_produccion BIGINT NULL DEFAULT NULL{}".format(
                        tbl_detalle.replace("`", "``"), after_clause
                    )
                )
                applied.append("Añadir id_lista_produccion en detalle")

            fk_name = "fk_detalle_agrupada_lista_produccion"
            if not fk_existe(cursor, tbl_detalle, fk_name):
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
# Registro para la UI y ejecución selectiva
# ---------------------------------------------------------------------------

ProviderFn = Callable[[Any], Dict[str, Any]]

PROVIDER_REGISTRY: List[Dict[str, Any]] = [
    {
        "id": "tiendanube_integration",
        "title": "Integración Tienda Nube",
        "description": (
            "Columnas id_tiendanube en tablas cliente y articulo para sincronización "
            "con Tienda Nube / Nuvemshop."
        ),
        "risk": "bajo",
        "run": run_tiendanube_integration_mysql,
    },
    {
        "id": "mpr_deposito_articulo",
        "title": "MPR — depósito y artículo",
        "description": (
            "Columnas deposito.suma_stock y articulo.stock_reserva (producción MPR). "
            "Ver docs/mpr/SCHEMA_MPR_ADMINISTRANET92.md."
        ),
        "risk": "bajo",
        "run": run_mpr_deposito_articulo_mysql,
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
        "id": "viajantes_objetivos_ventas",
        "title": "Objetivos de venta (cabecera + detalle)",
        "description": (
            "Tablas ``viajantes_objetivos_periodo`` (intervalo y anulado Si/No) y "
            "``viajantes_objetivos_ventas`` (detalle por cliente; ``id_periodo`` opcional en datos heredados)."
        ),
        "risk": "bajo",
        "run": run_viajantes_objetivos_ventas_mysql,
    },
]


def run_provider_by_id(provider_id: str, conn) -> Dict[str, Any]:
    for p in PROVIDER_REGISTRY:
        if p["id"] == provider_id:
            return p["run"](conn)
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

    for p in PROVIDER_REGISTRY:
        r = p["run"](conn)
        all_applied.extend(r.get("migrations_applied") or [])
        all_failed.extend(r.get("migrations_failed") or [])
        if r.get("message"):
            messages.append(f"[{p['id']}] {r['message']}")
        if not r.get("success", True):
            overall_ok = False

    return {
        "success": overall_ok and len(all_failed) == 0,
        "message": "\n".join(messages) if messages else mensaje_final(all_applied, all_failed),
        "migrations_applied": all_applied,
        "migrations_failed": all_failed,
    }
