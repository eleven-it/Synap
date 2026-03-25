# Tests de integración: consultas BO contra MySQL real.
# Validan que agregado y renglones usan el mismo filtro (fechas YYYYMMDD) y resultan consistentes.
#
# Ejecutar en contenedor (MySQL en misma red, ej. docker-compose.mysql.yml):
#   docker exec -e DB_HOST=mysql_administranet -e DB_PORT=3306 Synap_app python manage.py test reports.tests.test_bo_report_real_db
# Si la app ya tiene .env con DB_HOST apuntando a MySQL accesible, basta:
#   docker exec Synap_app python manage.py test reports.tests.test_bo_report_real_db

import unittest

from django.conf import settings

from reports.services.query_runner import (
    parse_fecha_bo_yyyymmdd,
    check_bo_agregado_vs_renglones_consistency,
)
from reports.services.connection_pool import get_mysql_pool


def _get_base_empresa():
    return getattr(settings, "DEFAULT_BASE_EMPRESA", None) or settings.DATABASES.get("mysql", {}).get("NAME", "administranet")


# SQL mínimo para consistencia: mismo WHERE que reporte BO (PED Pendiente, fechas, sin Gasto).
SQL_BO_AGREGADO_MIN = """
    SELECT
        a.id_manual AS codigo,
        SUM(sp.PrecioNetoxR) AS bo_importe
    FROM stockp sp
    INNER JOIN comp_ped cp ON cp.CodigoMovimiento = sp.CodigoMovimiento
    LEFT JOIN articulo a ON a.IDArt = sp.IDArt
    WHERE cp.TipoComprobante = 'PED'
      AND (sp.Comprobante = 'PED' OR sp.Comprobante IS NULL)
      AND cp.Anulado = 'No'
      AND (sp.anulado IS NULL OR sp.anulado = 'No')
      AND cp.Estado IN ('Pendiente')
      AND sp.CodigoMovimiento IS NOT NULL
      AND sp.Fecha >= %s AND sp.Fecha <= %s
      AND (a.IDArt IS NULL OR a.tipo_art IS NULL OR a.tipo_art <> 'Gasto')
    GROUP BY sp.IDArt, a.id_manual
    HAVING SUM(sp.Cantidad) > 0
"""
SQL_BO_ROWS_MIN = """
    SELECT
        COALESCE(a.id_manual, spr.id_manual, '') AS cod_manual,
        COALESCE(spr.PrecioNetoxR, 0) AS precio_x_renglon
    FROM comp_ped cp
    INNER JOIN stockp spr ON spr.CodigoMovimiento = cp.CodigoMovimiento
    LEFT JOIN articulo a ON a.IDArt = spr.IDArt
    WHERE cp.TipoComprobante = 'PED'
      AND (spr.Comprobante = 'PED' OR spr.Comprobante IS NULL)
      AND cp.Anulado = 'No'
      AND (spr.anulado IS NULL OR spr.anulado = 'No')
      AND cp.Estado IN ('Pendiente')
      AND spr.CodigoMovimiento IS NOT NULL
      AND spr.Fecha >= %s AND spr.Fecha <= %s
      AND (a.IDArt IS NULL OR a.tipo_art IS NULL OR a.tipo_art <> 'Gasto')
    ORDER BY cp.Fecha DESC, cp.NroComprobante ASC
"""


def run_bo_queries_real_db(fecha_inicio_bo: str, fecha_fin_bo: str):
    """
    Ejecuta las dos consultas BO contra MySQL (mismo camino que el reporte).
    Devuelve (backorder_detalle, backorder_detalle_rows) o (None, None) si no hay conexión.
    """
    base_empresa = _get_base_empresa()
    try:
        pool = get_mysql_pool()
        with pool.get_connection(base_empresa) as conn:
            cursor = conn.cursor()
            try:
                cursor.execute(SQL_BO_AGREGADO_MIN, [fecha_inicio_bo, fecha_fin_bo])
                agg_rows = cursor.fetchall()
                cursor.execute(SQL_BO_ROWS_MIN, [fecha_inicio_bo, fecha_fin_bo])
                row_rows = cursor.fetchall()
            finally:
                cursor.close()
        backorder_detalle = [
            {"codigo": (r[0] or "").strip(), "bo_importe": float(r[1] or 0)}
            for r in agg_rows
        ]
        backorder_detalle_rows = [
            {"cod_manual": (r[0] or "").strip(), "precio_x_renglon": float(r[1] or 0)}
            for r in row_rows
        ]
        return backorder_detalle, backorder_detalle_rows
    except Exception:
        return None, None


class TestBoReportRealDbConsistency(unittest.TestCase):
    """
    Ejecuta las consultas BO contra la base real con las mismas fechas (YYYYMMDD)
    y verifica que suma(precio_x_renglon) por código = bo_importe por artículo.
    Se omiten si MySQL no está configurado o no disponible.
    """

    def test_bo_agregado_vs_renglones_consistencia_con_fechas_yyyymmdd(self):
        """Mismas fechas YYYYMMDD en ambas consultas → sin inconsistencias."""
        fecha_inicio_bo, fecha_fin_bo = parse_fecha_bo_yyyymmdd("2026-01-01", "2026-03-02")
        self.assertEqual(fecha_inicio_bo, "20260101")
        self.assertEqual(fecha_fin_bo, "20260302")

        backorder_detalle, backorder_detalle_rows = run_bo_queries_real_db(fecha_inicio_bo, fecha_fin_bo)
        if backorder_detalle is None:
            self.skipTest("MySQL no disponible (conexión o ejecución fallida)")

        inconsistencies = check_bo_agregado_vs_renglones_consistency(
            backorder_detalle, backorder_detalle_rows, tolerance=0.01
        )
        self.assertEqual(
            inconsistencies,
            [],
            "Con fechas YYYYMMDD ambas consultas deben coincidir. Inconsistencias: %s" % inconsistencies,
        )

    def test_bo_articulo_5753_periodo_enero_marzo_2026(self):
        """Artículo 5753 (391586) en 20260101-20260302: bo_importe debe coincidir con suma de renglones."""
        fecha_inicio_bo, fecha_fin_bo = "20260101", "20260302"
        backorder_detalle, backorder_detalle_rows = run_bo_queries_real_db(fecha_inicio_bo, fecha_fin_bo)
        if backorder_detalle is None:
            self.skipTest("MySQL no disponible (conexión o ejecución fallida)")

        detalle_391586 = [r for r in backorder_detalle if (r.get("codigo") or "").strip() == "391586"]
        rows_391586 = [r for r in backorder_detalle_rows if (r.get("cod_manual") or "").strip() == "391586"]

        if not detalle_391586:
            self.skipTest("No hay datos de backorder para artículo 391586 en el período (base vacía o sin PED Pendiente)")
        bo_importe = float(detalle_391586[0].get("bo_importe") or 0)
        suma_renglones = sum(float(r.get("precio_x_renglon") or 0) for r in rows_391586)
        self.assertAlmostEqual(
            bo_importe,
            suma_renglones,
            places=2,
            msg="Art 391586: bo_importe=%s debe igualar suma(precio_x_renglon)=%s" % (bo_importe, suma_renglones),
        )
