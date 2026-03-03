# Tabla `reglas_precio_alta_art`

Base: **administranet**

---

## 1. Schema (information_schema)

### 1.1 Columnas

| Campo | Tipo | Nulo | PK | FK | Referencia |
|-------|------|------|----|----|------------|
| id_regla_precio_alta_art | DOUBLE | No | ✓ |  |  |
| id_articulo | DOUBLE | Sí |  |  |  |
| id_cliente | DOUBLE | Sí |  |  |  |
| tipo_regla | VARCHAR | Sí |  |  |  |
| tipo_calculo | VARCHAR | Sí |  |  |  |
| importe_regla | DECIMAL | Sí |  |  |  |
| vigencia_desde | DATE | Sí |  |  |  |
| vigencia_hasta | DATE | Sí |  |  |  |
| orden_regla | INT | Sí |  |  |  |
| id_rubro | DOUBLE | Sí |  |  |  |
| id_sub_rubro | DOUBLE | Sí |  |  |  |
| id_proveedor | DOUBLE | Sí |  |  |  |
| anulado | VARCHAR | Sí |  |  |  |
| prioridad_regla | VARCHAR | Sí |  |  |  |
| id_marca | DOUBLE | Sí |  |  |  |

### 1.2 Relaciones (FK del catálogo)

*No hay claves foráneas definidas en el catálogo para esta tabla.*

---

## 2. Relaciones inferidas desde consultas SQL

Relaciones detectadas por uso en código (JOINs en VB6 y Synap). Sirven para diseñar una DB normalizada.

*No se encontraron JOINs que involucren esta tabla en el código escaneado.*

---

## 3. Uso en AdministraNET (VB6)

Formularios y procedimientos que referencian esta tabla (lectura/escritura). Base para migración AdministraNET → Synap.

| Archivo | Línea | Operación | Fragmento |
|---------|-------|-----------|-----------|
| Cliente.frm | 4019 | SELECT | rs_regla.Open "SELECT * FROM reglas_precio_alta_art " & _ |
| Cliente.frm | 4305 | SELECT | rs_r.Open "SELECT * FROM reglas_precio_alta_art WHERE Anulad… |
| Cliente.frm | 4349 | SELECT | "FROM reglas_precio_alta_art " & _ |
| Cliente.frm | 4363 | SELECT | "FROM reglas_precio_alta_art " & _ |
| Cliente.frm | 4377 | SELECT | "FROM reglas_precio_alta_art " & _ |
| Cliente.frm | 4391 | SELECT | "FROM reglas_precio_alta_art " & _ |
| Cliente.frm | 4406 | SELECT | "FROM reglas_precio_alta_art " & _ |
| Cliente.frm | 4423 | SELECT | "FROM reglas_precio_alta_art " & _ |
| Cliente.frm | 4437 | SELECT | "FROM reglas_precio_alta_art " & _ |
| FacturaB_COPIA.frm | 16869 | SELECT | rs_regla.Open "SELECT * FROM reglas_precio_alta_art " & _ |
| FacturaB_COPIA.frm | 17172 | SELECT | rs_r.Open "SELECT * FROM reglas_precio_alta_art WHERE Anulad… |
| FacturaB_COPIA.frm | 17216 | SELECT | "FROM reglas_precio_alta_art " & _ |
| FacturaB_COPIA.frm | 17230 | SELECT | "FROM reglas_precio_alta_art " & _ |
| FacturaB_COPIA.frm | 17244 | SELECT | "FROM reglas_precio_alta_art " & _ |
| FacturaB_COPIA.frm | 17258 | SELECT | "FROM reglas_precio_alta_art " & _ |
| FacturaB_COPIA.frm | 17273 | SELECT | "FROM reglas_precio_alta_art " & _ |
| FacturaB_COPIA.frm | 17290 | SELECT | "FROM reglas_precio_alta_art " & _ |
| FacturaB_COPIA.frm | 17304 | SELECT | "FROM reglas_precio_alta_art " & _ |
| Rprecios_abm.frm | 2737 | SELECT | conn.Execute "DELETE FROM reglas_precio_alta_art WHERE id_re… |
| Rprecios_abm.frm | 2737 | DELETE | conn.Execute "DELETE FROM reglas_precio_alta_art WHERE id_re… |
| Rprecios_abm.frm | 2879 | SELECT | "FROM reglas_precio_alta_art " & _ |
| TPV.frm | 34082 | SELECT | rs_regla.Open "SELECT * FROM reglas_precio_alta_art " & _ |
| TPV.frm | 34418 | SELECT | rs_r.Open "SELECT * FROM reglas_precio_alta_art WHERE Anulad… |
| TPV.frm | 34466 | SELECT | "FROM reglas_precio_alta_art " & _ |
| TPV.frm | 34480 | SELECT | "FROM reglas_precio_alta_art " & _ |
| TPV.frm | 34494 | SELECT | "FROM reglas_precio_alta_art " & _ |
| TPV.frm | 34508 | SELECT | "FROM reglas_precio_alta_art " & _ |
| TPV.frm | 34522 | SELECT | "FROM reglas_precio_alta_art " & _ |
| TPV.frm | 34537 | SELECT | "FROM reglas_precio_alta_art " & _ |
| TPV.frm | 34554 | SELECT | "FROM reglas_precio_alta_art " & _ |
| TPV.frm | 34568 | SELECT | "FROM reglas_precio_alta_art " & _ |
| TPV.frm | 34582 | SELECT | "FROM reglas_precio_alta_art " & _ |
| TPV.frm | 34662 | SELECT | '            rs_regla.Open "SELECT * FROM reglas_precio_alta… |
| TPV.frm | 34959 | SELECT | '    rs_r.Open "SELECT * FROM reglas_precio_alta_art WHERE A… |
| TPV.frm | 35003 | SELECT | '                      "FROM reglas_precio_alta_art " & _ |
| TPV.frm | 35017 | SELECT | '                      "FROM reglas_precio_alta_art " & _ |
| TPV.frm | 35031 | SELECT | '                      "FROM reglas_precio_alta_art " & _ |
| TPV.frm | 35045 | SELECT | '                      "FROM reglas_precio_alta_art " & _ |
| TPV.frm | 35060 | SELECT | '                      "FROM reglas_precio_alta_art " & _ |
| TPV.frm | 35077 | SELECT | '                      "FROM reglas_precio_alta_art " & _ |
| TPV.frm | 35091 | SELECT | '                      "FROM reglas_precio_alta_art " & _ |
| Modifica_LP_Global.frm | 1859 | SELECT | rs_regla.Open "SELECT * FROM reglas_precio_alta_art " & _ |
| Modifica_LP_Global.frm | 2115 | SELECT | rs_r.Open "SELECT * FROM reglas_precio_alta_art WHERE Anulad… |
| Modifica_LP_Global.frm | 2159 | SELECT | "FROM reglas_precio_alta_art " & _ |
| Modifica_LP_Global.frm | 2173 | SELECT | "FROM reglas_precio_alta_art " & _ |
| Modifica_LP_Global.frm | 2187 | SELECT | "FROM reglas_precio_alta_art " & _ |
| Modifica_LP_Global.frm | 2201 | SELECT | "FROM reglas_precio_alta_art " & _ |
| Modifica_LP_Global.frm | 2216 | SELECT | "FROM reglas_precio_alta_art " & _ |
| Modifica_LP_Global.frm | 2233 | SELECT | "FROM reglas_precio_alta_art " & _ |
| Modifica_LP_Global.frm | 2247 | SELECT | "FROM reglas_precio_alta_art " & _ |
| Importador_Excel.frm | 1021 | SELECT | rs_regla.Open "SELECT * FROM reglas_precio_alta_art " & _ |
| Importador_Excel.frm | 1339 | SELECT | rs_r.Open "SELECT * FROM reglas_precio_alta_art WHERE Anulad… |
| Importador_Excel.frm | 1387 | SELECT | "FROM reglas_precio_alta_art " & _ |
| Importador_Excel.frm | 1401 | SELECT | "FROM reglas_precio_alta_art " & _ |
| Importador_Excel.frm | 1415 | SELECT | "FROM reglas_precio_alta_art " & _ |
| Importador_Excel.frm | 1429 | SELECT | "FROM reglas_precio_alta_art " & _ |
| Importador_Excel.frm | 1443 | SELECT | "FROM reglas_precio_alta_art " & _ |
| Importador_Excel.frm | 1458 | SELECT | "FROM reglas_precio_alta_art " & _ |
| Importador_Excel.frm | 1475 | SELECT | "FROM reglas_precio_alta_art " & _ |
| Importador_Excel.frm | 1489 | SELECT | "FROM reglas_precio_alta_art " & _ |
| Importador_Excel.frm | 1503 | SELECT | "FROM reglas_precio_alta_art " & _ |
| Visualiza_Pedido.frm | 11883 | SELECT | rs_regla.Open "SELECT * FROM reglas_precio_alta_art " & _ |
| Visualiza_Pedido.frm | 12219 | SELECT | rs_r.Open "SELECT * FROM reglas_precio_alta_art WHERE Anulad… |
| Visualiza_Pedido.frm | 12267 | SELECT | "FROM reglas_precio_alta_art " & _ |
| Visualiza_Pedido.frm | 12281 | SELECT | "FROM reglas_precio_alta_art " & _ |
| Visualiza_Pedido.frm | 12295 | SELECT | "FROM reglas_precio_alta_art " & _ |
| Visualiza_Pedido.frm | 12309 | SELECT | "FROM reglas_precio_alta_art " & _ |
| Visualiza_Pedido.frm | 12323 | SELECT | "FROM reglas_precio_alta_art " & _ |
| Visualiza_Pedido.frm | 12338 | SELECT | "FROM reglas_precio_alta_art " & _ |
| Visualiza_Pedido.frm | 12355 | SELECT | "FROM reglas_precio_alta_art " & _ |
| Visualiza_Pedido.frm | 12369 | SELECT | "FROM reglas_precio_alta_art " & _ |
| Visualiza_Pedido.frm | 12383 | SELECT | "FROM reglas_precio_alta_art " & _ |
| CargaArticulo_Original.frm | 12288 | SELECT | '    rs_r.Open "SELECT * FROM reglas_precio_alta_art WHERE A… |
| CargaArticulo_Original.frm | 12304 | SELECT | '            rs_r.Open "SELECT id_regla_precio_alta_art FROM… |
| CargaArticulo_Original.frm | 12317 | SELECT | '            rs_r.Open "SELECT id_regla_precio_alta_art FROM… |
| CargaArticulo_Original.frm | 12330 | SELECT | '            rs_r.Open "SELECT id_regla_precio_alta_art FROM… |
| CargaArticulo_Original.frm | 12343 | SELECT | '            rs_r.Open "SELECT id_regla_precio_alta_art FROM… |
| CargaArticulo_Original.frm | 12357 | SELECT | '            rs_r.Open "SELECT id_regla_precio_alta_art FROM… |
| CargaArticulo_Original.frm | 12373 | SELECT | '            rs_r.Open "SELECT id_regla_precio_alta_art FROM… |
| CargaArticulo_Original.frm | 12386 | SELECT | '            rs_r.Open "SELECT id_regla_precio_alta_art FROM… |
| … | … | … | *(279 referencias más)* |

---

## 4. Uso en Synap (reports)

*No se encontraron referencias en el módulo reports.*

[← Índice de tablas](../DB_INDICE_TABLAS.md)