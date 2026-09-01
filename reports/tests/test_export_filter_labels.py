# -*- coding: utf-8 -*-
"""Tests etiquetas de filtros en exportación Excel."""
from unittest.mock import MagicMock, patch

from django.test import SimpleTestCase

from reports.services.export_filter_labels import (
    _fmt_fecha,
    _label_lista_precio,
    build_export_filter_lines,
)


class ExportFilterLabelsTest(SimpleTestCase):
    def test_fmt_fecha_iso(self):
        self.assertEqual(_fmt_fecha("2025-03-15"), "15/03/2025")

    def test_lista_precio_desde_meta(self):
        self.assertEqual(_label_lista_precio(2, "Lista Oficial"), "Lista Oficial")

    def test_fechas_sin_mysql(self):
        lines = build_export_filter_lines(
            "ventas_netas",
            {
                "filters": {
                    "fecha_inicio": "2025-01-01",
                    "fecha_fin": "2025-01-31",
                }
            },
            {},
            None,
        )
        labels = dict(lines)
        self.assertEqual(labels.get("Período desde"), "01/01/2025")
        self.assertEqual(labels.get("Período hasta"), "31/01/2025")

    def test_orden_y_lista_precio_label(self):
        lines = build_export_filter_lines(
            "ventas-objetivos-vs-bo",
            {
                "filters": {
                    "ordenar_por": "objetivo_meta",
                    "orden_forma": "desc",
                    "lista_precio": 1,
                }
            },
            {"lista_precio_label": "Lista 1"},
            None,
        )
        labels = dict(lines)
        self.assertEqual(labels.get("Ordenar por"), "Objetivo meta")
        self.assertEqual(labels.get("Orden"), "Decreciente")
        self.assertEqual(labels.get("Lista de precio"), "Lista 1")

    @patch("reports.services.export_filter_labels._MysqlLabelLookup")
    def test_resuelve_sucursales_por_nombre(self, lookup_cls):
        inst = MagicMock()
        inst.labels_for.return_value = ["Sucursal Centro", "Sucursal Norte"]
        lookup_cls.return_value = inst

        lines = build_export_filter_lines(
            "ventas-por-articulo",
            {"filters": {"sucursales": [1, 2]}},
            {},
            "empresa_test",
        )
        labels = dict(lines)
        self.assertEqual(labels.get("Sucursales"), "Sucursal Centro, Sucursal Norte")
        inst.labels_for.assert_called()

    def test_ventas_sin_seleccion_declara_todas_sucursales_y_pv(self):
        lines = build_export_filter_lines(
            "ventas-por-vendedor",
            {"filters": {"fecha_inicio_facturacion": "2026-08-01"}},
            {},
            None,
        )
        labels = dict(lines)
        self.assertEqual(labels.get("Sucursales"), "Todas")
        self.assertEqual(labels.get("Puntos de venta"), "Todos")

    def test_slug_sin_alcance_no_fuerza_todas(self):
        lines = build_export_filter_lines(
            "stock-existencias",
            {"filters": {"fecha_inicio": "2026-08-01"}},
            {},
            None,
        )
        labels = dict(lines)
        self.assertNotIn("Sucursales", labels)
        self.assertNotIn("Puntos de venta", labels)

    def test_punto_venta_id_escalar_entra_en_alcance(self):
        lines = build_export_filter_lines(
            "ventas-netas",
            {"filters": {"punto_venta_id": 7, "sucursales": []}},
            {},
            None,
        )
        labels = dict(lines)
        self.assertEqual(labels.get("Sucursales"), "Todas")
        self.assertEqual(labels.get("Puntos de venta"), "7")

    def test_filter_labels_extra_en_payload(self):
        lines = build_export_filter_lines(
            "comprobantes-rutas",
            {"filters": {"filter_labels": {"Ruta": "Ruta Norte"}}},
            {},
            None,
        )
        self.assertIn(("Ruta", "Ruta Norte"), lines)
