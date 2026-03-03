# Tabla `reglas_precio`

Base: **administranet**

---

## 1. Schema (information_schema)

### 1.1 Columnas

| Campo | Tipo | Nulo | PK | FK | Referencia |
|-------|------|------|----|----|------------|
| id_regla_precio | DOUBLE | No | ✓ |  |  |
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
| promocion_cant | DECIMAL | Sí |  |  |  |
| promocion_por | DECIMAL | Sí |  |  |  |
| id_regla_precio_alta_art | DOUBLE | Sí |  |  |  |
| id_regla_precio_masivas | DOUBLE | Sí |  |  |  |
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
| Cliente.frm | 3888 | SELECT | '        rs_regla.Open "SELECT * FROM reglas_precio " & _ |
| Cliente.frm | 3991 | SELECT | "FROM reglas_precio " & _ |
| FacturaB_COPIA.frm | 7425 | SELECT | rs_prom.Open "SELECT promocion_por, promocion_cant FROM regl… |
| FacturaB_COPIA.frm | 7611 | SELECT | rs_prom.Open "SELECT promocion_por, promocion_cant FROM regl… |
| FacturaB_COPIA.frm | 16724 | SELECT | '        rs_regla.Open "SELECT * FROM reglas_precio " & _ |
| FacturaB_COPIA.frm | 16776 | SELECT | '                rs_prom.Open "SELECT promocion_por, promoci… |
| FacturaB_COPIA.frm | 16841 | SELECT | "FROM reglas_precio " & _ |
| FacturaB_COPIA.frm | 16952 | SELECT | rs_prom.Open "SELECT promocion_por, promocion_cant FROM regl… |
| Rprecios_abm.frm | 2080 | SELECT | '    DataRprecios.RecordSource = " SELECT * FROM reglas_prec… |
| Rprecios_abm.frm | 2708 | SELECT | conn.Execute "DELETE FROM reglas_precio WHERE id_regla_preci… |
| Rprecios_abm.frm | 2708 | DELETE | conn.Execute "DELETE FROM reglas_precio WHERE id_regla_preci… |
| Rprecios_abm.frm | 2842 | SELECT | "FROM reglas_precio " & _ |
| Rprecios_abm.frm | 3059 | SELECT | conn.Execute "DELETE FROM reglas_precio WHERE id_cliente = "… |
| Rprecios_abm.frm | 3059 | DELETE | conn.Execute "DELETE FROM reglas_precio WHERE id_cliente = "… |
| TPV.frm | 16201 | SELECT | rs_prom.Open "SELECT promocion_por, promocion_cant FROM regl… |
| TPV.frm | 16501 | SELECT | rs_prom.Open "SELECT promocion_por, promocion_cant FROM regl… |
| TPV.frm | 21105 | SELECT | rs_prom.Open "SELECT promocion_por, promocion_cant FROM regl… |
| TPV.frm | 34054 | SELECT | "FROM reglas_precio " & _ |
| TPV.frm | 34163 | SELECT | rs_prom.Open "SELECT promocion_por, promocion_cant FROM regl… |
| TPV.frm | 34634 | SELECT | '                      "FROM reglas_precio " & _ |
| TPV.frm | 34739 | SELECT | '                rs_prom.Open "SELECT promocion_por, promoci… |
| Modifica_LP_Global.frm | 1740 | SELECT | '        rs_regla.Open "SELECT * FROM reglas_precio " & _ |
| Modifica_LP_Global.frm | 1831 | SELECT | "FROM reglas_precio " & _ |
| Importador_Excel.frm | 993 | SELECT | "FROM reglas_precio " & _ |
| Importador_Excel.frm | 1085 | SELECT | rs_prom.Open "SELECT promocion_por, promocion_cant FROM regl… |
| Visualiza_Pedido.frm | 5308 | SELECT | rs_prom.Open "SELECT promocion_por, promocion_cant FROM regl… |
| Visualiza_Pedido.frm | 5461 | SELECT | rs_prom.Open "SELECT promocion_por, promocion_cant FROM regl… |
| Visualiza_Pedido.frm | 11737 | SELECT | '        rs_regla.Open "SELECT * FROM reglas_precio " & _ |
| Visualiza_Pedido.frm | 11788 | SELECT | '                rs_prom.Open "SELECT promocion_por, promoci… |
| Visualiza_Pedido.frm | 11855 | SELECT | "FROM reglas_precio " & _ |
| Visualiza_Pedido.frm | 11964 | SELECT | rs_prom.Open "SELECT promocion_por, promocion_cant FROM regl… |
| CargaArticulo_Original.frm | 12411 | INSERT | ''        conn.Execute "INSERT INTO reglas_precio(id_articul… |
| CargaArticulo_Original.frm | 12416 | SELECT | '                                          "(SELECT DISTINCT… |
| CargaArticulo_Original.frm | 12422 | INSERT | '        conn.Execute "INSERT INTO reglas_precio(id_articulo… |
| CargaArticulo_Original.frm | 12427 | SELECT | '                                          "(SELECT DISTINCT… |
| CargaArticulo_Original.frm | 12434 | INSERT | '        conn.Execute "INSERT INTO reglas_precio(id_articulo… |
| CargaArticulo_Original.frm | 12438 | SELECT | '                            "From reglas_precio " & _ |
| CargaArticulo_Original.frm | 12451 | SELECT | '                                          "(SELECT DISTINCT… |
| CargaArticulo_Original.frm | 13421 | SELECT | '                          "FROM reglas_precio WHERE " & _ |
| CargaArticulo_Original.frm | 13429 | INSERT | '            conn.Execute "INSERT INTO reglas_precio(id_arti… |
| CargaArticulo_Original.frm | 13433 | SELECT | '                                "From reglas_precio " & _ |
| Rprecios_alta_art.frm | 2197 | INSERT | '        conn.Execute "INSERT INTO reglas_precio(id_articulo… |
| Rprecios_alta_art.frm | 2209 | JOIN | '                                              "INNER JOIN r… |
| Articulo.frm | 9225 | SELECT | '      rs_regla.Open "SELECT * FROM reglas_precio " & _ |
| Articulo.frm | 10099 | SELECT | "FROM reglas_precio " & _ |
| Articulo.frm | 10607 | SELECT | rs_prom.Open "SELECT promocion_por, promocion_cant FROM regl… |
| Articulo.frm | 10840 | SELECT | rs_prom.Open "SELECT promocion_por, promocion_cant FROM regl… |
| Articulo.frm | 10932 | SELECT | "FROM reglas_precio " & _ |
| Articulo.frm | 11056 | SELECT | rs_prom.Open "SELECT promocion_por, promocion_cant FROM regl… |
| Articulo.frm | 11553 | SELECT | rs_prom.Open "SELECT promocion_por, promocion_cant FROM regl… |
| Articulo.frm | 12436 | SELECT | rs_prom.Open "SELECT promocion_por, promocion_cant FROM regl… |
| Articulo.frm | 12694 | SELECT | rs_prom.Open "SELECT promocion_por, promocion_cant FROM regl… |
| Articulo.frm | 13443 | SELECT | rs_prom.Open "SELECT promocion_por, promocion_cant FROM regl… |
| Articulo.frm | 13701 | SELECT | rs_prom.Open "SELECT promocion_por, promocion_cant FROM regl… |
| Articulo.frm | 14445 | SELECT | rs_prom.Open "SELECT promocion_por, promocion_cant FROM regl… |
| Articulo.frm | 14703 | SELECT | rs_prom.Open "SELECT promocion_por, promocion_cant FROM regl… |
| Articulo.frm | 15444 | SELECT | rs_prom.Open "SELECT promocion_por, promocion_cant FROM regl… |
| Articulo.frm | 15702 | SELECT | rs_prom.Open "SELECT promocion_por, promocion_cant FROM regl… |
| Articulo.frm | 16443 | SELECT | rs_prom.Open "SELECT promocion_por, promocion_cant FROM regl… |
| Articulo.frm | 16657 | SELECT | rs_prom.Open "SELECT promocion_por, promocion_cant FROM regl… |
| FacturaB.frm | 12465 | SELECT | rs_prom.Open "SELECT promocion_por, promocion_cant FROM regl… |
| FacturaB.frm | 12666 | SELECT | rs_prom.Open "SELECT promocion_por, promocion_cant FROM regl… |
| FacturaB.frm | 22798 | SELECT | '        rs_regla.Open "SELECT * FROM reglas_precio " & _ |
| FacturaB.frm | 22850 | SELECT | '                rs_prom.Open "SELECT promocion_por, promoci… |
| FacturaB.frm | 22915 | SELECT | '                      "FROM reglas_precio " & _ |
| FacturaB.frm | 23026 | SELECT | '                rs_prom.Open "SELECT promocion_por, promoci… |
| FacturaB.frm | 23430 | SELECT | "FROM reglas_precio " & _ |
| FacturaB.frm | 23539 | SELECT | rs_prom.Open "SELECT promocion_por, promocion_cant FROM regl… |
| NotaCred_SinCompO.frm | 7697 | SELECT | rs_prom.Open "SELECT promocion_por, promocion_cant FROM regl… |
| NotaCred_SinCompO.frm | 7832 | SELECT | rs_prom.Open "SELECT promocion_por, promocion_cant FROM regl… |
| NotaCred_SinCompO.frm | 15370 | SELECT | '                      "FROM reglas_precio " & _ |
| NotaCred_SinCompO.frm | 15481 | SELECT | '                rs_prom.Open "SELECT promocion_por, promoci… |
| NotaCred_SinCompO.frm | 15885 | SELECT | "FROM reglas_precio " & _ |
| NotaCred_SinCompO.frm | 15994 | SELECT | rs_prom.Open "SELECT promocion_por, promocion_cant FROM regl… |
| FacturaA.frm | 7912 | SELECT | rs_prom.Open "SELECT promocion_por, promocion_cant FROM regl… |
| FacturaA.frm | 8115 | SELECT | rs_prom.Open "SELECT promocion_por, promocion_cant FROM regl… |
| FacturaA.frm | 19410 | SELECT | '        rs_regla.Open "SELECT * FROM reglas_precio " & _ |
| FacturaA.frm | 19462 | SELECT | '                rs_prom.Open "SELECT promocion_por, promoci… |
| FacturaA.frm | 19527 | SELECT | '                      "FROM reglas_precio " & _ |
| FacturaA.frm | 19638 | SELECT | '                rs_prom.Open "SELECT promocion_por, promoci… |
| … | … | … | *(129 referencias más)* |

---

## 4. Uso en Synap (reports)

*No se encontraron referencias en el módulo reports.*

[← Índice de tablas](../DB_INDICE_TABLAS.md)