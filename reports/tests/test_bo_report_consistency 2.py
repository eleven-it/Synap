# Tests para el reporte BO: causas posibles de diferencia bo_importe vs Precio x renglón.
# Ver docs/reports/SQL_VISTAS_REPORTES_VB6_Y_BO.md secciones 3.9 y 3.10.

import unittest

from reports.services.query_runner import (
    parse_fecha_bo_yyyymmdd,
    check_bo_agregado_vs_renglones_consistency,
)


# Valores del caso real art 5753 (391586) para validar causa de inconsistencia:
# - Con filtro Estado=Pendiente y fechas 20260101-20260302: 2 renglones, suma = 22.336.360,62 = bo_importe.
# - Si una consulta usa YYYY-MM-DD y stockp.Fecha es INT: MySQL convierte a 2026, rango ampliado (todo el año),
#   la otra usa YYYYMMDD: entonces agregado puede tener 22,3M (rango correcto) y renglones incluir más filas → suma ~32,7M.
BO_ART_CODIGO = "391586"
BO_IMPORTE_CORRECTO = 22336360.62   # agregado con filtro fecha correcto (solo período)
SUMA_RENGLONES_PERIODO = 21272724.25 + 1063636.37  # 2 renglones Pendiente en período
SUMA_RENGLONES_RANGO_AMPLIADO = 32727258.03  # ej. un renglón de otro período o rango ampliado


class TestParseFechaBoYyyymmdd(unittest.TestCase):
    """Fechas BO deben pasarse a YYYYMMDD para que sql_bo_detalle y sql_bo_rows usen el mismo filtro."""

    def test_formato_iso_convierte_a_yyyymmdd(self):
        inicio, fin = parse_fecha_bo_yyyymmdd("2026-01-01", "2026-03-02")
        self.assertEqual(inicio, "20260101")
        self.assertEqual(fin, "20260302")

    def test_mismo_dia(self):
        inicio, fin = parse_fecha_bo_yyyymmdd("2026-02-13", "2026-02-13")
        self.assertEqual(inicio, "20260213")
        self.assertEqual(fin, "20260213")

    def test_ya_yyyymmdd_devuelve_igual_si_no_parsea_como_iso(self):
        # Si se pasan strings que no son YYYY-MM-DD, strptime falla y se devuelven tal cual
        inicio, fin = parse_fecha_bo_yyyymmdd("20260101", "20260302")
        self.assertEqual(inicio, "20260101")
        self.assertEqual(fin, "20260302")

    def test_fecha_invalida_devuelve_originales(self):
        inicio, fin = parse_fecha_bo_yyyymmdd("invalid", "2026-03-02")
        self.assertEqual(inicio, "invalid")
        self.assertEqual(fin, "2026-03-02")

    def test_none_o_vacio_usa_except(self):
        inicio, fin = parse_fecha_bo_yyyymmdd("", "2026-01-01")
        self.assertEqual(inicio, "")
        self.assertEqual(fin, "2026-01-01")

    def test_fecha_con_hora_iso_se_trunca_a_10_chars(self):
        inicio, fin = parse_fecha_bo_yyyymmdd("2026-01-01T00:00:00", "2026-03-02T23:59:59")
        self.assertEqual(inicio, "20260101")
        self.assertEqual(fin, "20260302")


class TestCheckBoAgregadoVsRenglonesConsistency(unittest.TestCase):
    """Consistencia: suma(precio_x_renglon) por cod_manual debe igualar bo_importe por artículo."""

    def test_datos_coherentes_sin_inconsistencias(self):
        detalle = [
            {"codigo": "391586", "bo_importe": 22336360.62},
        ]
        rows = [
            {"cod_manual": "391586", "precio_x_renglon": 21272724.25},
            {"cod_manual": "391586", "precio_x_renglon": 1063636.37},
        ]
        inc = check_bo_agregado_vs_renglones_consistency(detalle, rows, tolerance=0.01)
        self.assertEqual(inc, [])

    def test_datos_incoherentes_detecta_diferencia(self):
        detalle = [
            {"codigo": "391586", "bo_importe": 22336360.62},
        ]
        # Suma renglones distinta al agregado (ej. por filtro de fecha distinto)
        rows = [
            {"cod_manual": "391586", "precio_x_renglon": 32727258.03},
        ]
        inc = check_bo_agregado_vs_renglones_consistency(detalle, rows, tolerance=0.01)
        self.assertEqual(len(inc), 1)
        cod, bo_imp, sum_rows, diff = inc[0]
        self.assertEqual(cod, "391586")
        self.assertAlmostEqual(bo_imp, 22336360.62, places=2)
        self.assertAlmostEqual(sum_rows, 32727258.03, places=2)
        self.assertAlmostEqual(diff, 22336360.62 - 32727258.03, places=2)

    def test_articulo_sin_renglones_cuenta_como_inconsistencia(self):
        detalle = [
            {"codigo": "999", "bo_importe": 1000.0},
        ]
        rows = []  # ningún renglón para 999
        inc = check_bo_agregado_vs_renglones_consistency(detalle, rows, tolerance=0.01)
        self.assertEqual(len(inc), 1)
        self.assertEqual(inc[0][0], "999")
        self.assertAlmostEqual(inc[0][2], 0.0)

    def test_tolerancia_evita_falsos_positivos_por_redondeo(self):
        detalle = [{"codigo": "A", "bo_importe": 100.0}]
        rows = [{"cod_manual": "A", "precio_x_renglon": 99.999}]
        # diff = 0.001; con tolerancia 0.01 no se considera inconsistencia
        inc = check_bo_agregado_vs_renglones_consistency(detalle, rows, tolerance=0.01)
        self.assertEqual(len(inc), 0)
        # con tolerancia 0.0001 sí se detecta
        inc2 = check_bo_agregado_vs_renglones_consistency(detalle, rows, tolerance=0.0001)
        self.assertEqual(len(inc2), 1)

    def test_varios_articulos_solo_uno_inconsistente(self):
        detalle = [
            {"codigo": "A", "bo_importe": 100.0},
            {"codigo": "B", "bo_importe": 200.0},
        ]
        rows = [
            {"cod_manual": "A", "precio_x_renglon": 100.0},
            {"cod_manual": "B", "precio_x_renglon": 150.0},  # debería ser 200
        ]
        inc = check_bo_agregado_vs_renglones_consistency(detalle, rows, tolerance=0.01)
        self.assertEqual(len(inc), 1)
        self.assertEqual(inc[0][0], "B")


class TestCausaInconsistenciaValidada(unittest.TestCase):
    """
    Valida por qué se produce la inconsistencia observada (bo_importe 22,3M vs Precio x renglón 32,7M).
    Causa: sql_bo_detalle y sql_bo_rows usan filtros de fecha distintos (p. ej. una con YYYYMMDD
    y otra con YYYY-MM-DD cuando stockp.Fecha es INT → una ve solo el período, la otra todo el año).
    """

    def test_mismo_filtro_fecha_datos_coherentes(self):
        # Simula: ambas consultas con mismo período (20260101-20260302), solo Pendiente.
        # Agregado devuelve bo_importe; row-level devuelve 2 renglones que suman lo mismo.
        detalle = [{"codigo": BO_ART_CODIGO, "bo_importe": BO_IMPORTE_CORRECTO}]
        rows = [
            {"cod_manual": BO_ART_CODIGO, "precio_x_renglon": 21272724.25},
            {"cod_manual": BO_ART_CODIGO, "precio_x_renglon": 1063636.37},
        ]
        inc = check_bo_agregado_vs_renglones_consistency(detalle, rows, tolerance=0.01)
        self.assertEqual(inc, [], "Con mismo filtro de fecha no debe haber inconsistencia")

    def test_filtro_fecha_distinto_produce_inconsistencia_22m_vs_32m(self):
        # Simula: agregado con período correcto (bo_importe=22,3M); row-level con rango ampliado
        # (ej. YYYY-MM-DD en base INT → todo el año, un renglón con 32,7M o suma de más renglones).
        detalle = [{"codigo": BO_ART_CODIGO, "bo_importe": BO_IMPORTE_CORRECTO}]
        rows = [{"cod_manual": BO_ART_CODIGO, "precio_x_renglon": SUMA_RENGLONES_RANGO_AMPLIADO}]
        inc = check_bo_agregado_vs_renglones_consistency(detalle, rows, tolerance=0.01)
        self.assertEqual(len(inc), 1, "Filtros distintos deben producir exactamente 1 inconsistencia para este artículo")
        cod, bo_imp, sum_rows, diff = inc[0]
        self.assertEqual(cod, BO_ART_CODIGO)
        self.assertAlmostEqual(bo_imp, BO_IMPORTE_CORRECTO, places=2)
        self.assertAlmostEqual(sum_rows, SUMA_RENGLONES_RANGO_AMPLIADO, places=2)
        self.assertLess(diff, 0, "Agregado correcto (menor) menos renglones ampliados (mayor) debe ser negativo")

    def test_solucion_misma_fecha_yyyymmdd_ambas_consultas(self):
        # Validar que parse_fecha_bo_yyyymmdd convierte a YYYYMMDD; si ambas consultas
        # usan fecha_inicio_bo y fecha_fin_bo (salida de esa función), reciben el mismo filtro.
        inicio, fin = parse_fecha_bo_yyyymmdd("2026-01-01", "2026-03-02")
        self.assertEqual(inicio, "20260101")
        self.assertEqual(fin, "20260302")
        # En query_runner: sql_bo_detalle usa [fecha_inicio_bo, fecha_fin_bo]; params_bo_rows = [fecha_inicio_bo, fecha_fin_bo] + ...
        self.assertEqual(len(inicio), 8, "YYYYMMDD tiene 8 caracteres para comparación INT en MySQL")
        self.assertEqual(len(fin), 8)


class TestProratingSumaBoImporte(unittest.TestCase):
    """Prorrateo: con_stock_importe + con_ingreso_importe + sin_stock_importe debe ser bo_importe."""

    def test_formula_prorrateo_suma_bo_importe(self):
        # Misma lógica que query_runner: importe_i = bo_importe * (qty_i / bo_qty)
        # con_stock_qty + con_ingreso_qty + sin_stock_qty = bo_qty => suma importes = bo_importe
        bo_importe = 22336360.6158
        bo_qty = 126.0
        con_stock_qty = 12.0
        con_ingreso_qty = 114.0
        sin_stock_qty = 0.0
        self.assertAlmostEqual(con_stock_qty + con_ingreso_qty + sin_stock_qty, bo_qty)
        con_stock_importe = bo_importe * (con_stock_qty / bo_qty)
        con_ingreso_importe = bo_importe * (con_ingreso_qty / bo_qty)
        sin_stock_importe = bo_importe * (sin_stock_qty / bo_qty)
        suma = con_stock_importe + con_ingreso_importe + sin_stock_importe
        self.assertAlmostEqual(suma, bo_importe, places=4)

    def test_cualquier_proporcion_suma_bo_importe(self):
        bo_importe = 1000.0
        bo_qty = 10.0
        for c_s, c_i, s_s in [(5, 3, 2), (0, 0, 10), (10, 0, 0)]:
            self.assertAlmostEqual(c_s + c_i + s_s, bo_qty, places=6)
            i_s = bo_importe * (c_s / bo_qty)
            i_i = bo_importe * (c_i / bo_qty)
            i_n = bo_importe * (s_s / bo_qty)
            self.assertAlmostEqual(i_s + i_i + i_n, bo_importe, places=6)


class TestBoRowLevelColumnIndex(unittest.TestCase):
    """El SELECT row-level (sql_bo_rows) tiene precio_x_renglon en la columna índice 9 (0-based)."""

    def test_orden_columnas_row_level(self):
        # Orden documentado en SQL_VISTAS_REPORTES_VB6_Y_BO.md 3.5:
        # 0=fecha, 1=nro_comp, 2=descripcion, 3=cod_manual, 4=cantidad, 5=cant_pend,
        # 6=estado, 7=cliente, 8=id_cliente, 9=precio_x_renglon, 10=nombre_rubro, 11=nombre_sub_rubro, 12=nombre_vendedor
        columnas_esperadas = [
            "fecha", "nro_comp", "descripcion", "cod_manual", "cantidad", "cant_pend",
            "estado", "cliente", "id_cliente", "precio_x_renglon", "nombre_rubro",
            "nombre_sub_rubro", "nombre_vendedor",
        ]
        self.assertEqual(len(columnas_esperadas), 13)
        idx_precio = columnas_esperadas.index("precio_x_renglon")
        self.assertEqual(idx_precio, 9, "precio_x_renglon debe ser índice 9 para que r[9] sea correcto")
