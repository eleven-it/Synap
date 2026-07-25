# Tabla `lote_stock`

Base: **administranet**

---

## 1. Schema (information_schema)

### 1.1 Columnas

| Campo | Tipo | Nulo | PK | FK | Referencia |
|-------|------|------|----|----|------------|
| id_lote_stock | DOUBLE | No | ✓ |  |  |
| id_lote | DOUBLE | Sí |  |  |  |
| stock_lote | DECIMAL | Sí |  |  |  |
| id_deposito | INT | Sí |  |  |  |

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
| PNotaCred.frm | 3246 | SELECT | rs_lote.Open "SELECT * from lote_stock where id_lote = " & C… |
| PNotaCred.frm | 3286 | SELECT | rs_lote.Open "SELECT * from lote_stock where id_lote = " & i… |
| Visualiza_NotaCred.frm | 3440 | JOIN | '        "INNER JOIN lote_stock ON (lote.id_lote = lote_stoc… |
| Visualiza_CargaMovStock.frm | 3069 | SELECT | rs_lotestock.Open "Select * From lote_stock where id_lote = … |
| Visualiza_CargaMovStock.frm | 3126 | SELECT | rs_lote.Open "SELECT * from lote_stock where id_lote_stock=0… |
| Visualiza_CargaMovStock.frm | 3142 | JOIN | "INNER JOIN lote_stock ON (lote.id_lote = lote_stock.id_lote… |
| Visualiza_CargaMovStock.frm | 3290 | SELECT | rs_lote.Open "SELECT * FROM lote_stock WHERE id_lote ='" & C… |
| Visualiza_CargaMovStock.frm | 4045 | JOIN | "INNER JOIN lote_stock on (lote.id_lote = lote_stock.id_lote… |
| Visualiza_CargaMovStock.frm | 4449 | JOIN | "INNER JOIN lote_stock on (lote.id_lote = lote_stock.id_lote… |
| FacturaB_COPIA.frm | 4723 | JOIN | "INNER JOIN lote_stock ON (lote.id_lote = lote_stock.id_lote… |
| FacturaB_COPIA.frm | 4774 | JOIN | "INNER JOIN lote_stock ON (lote.id_lote = lote_stock.id_lote… |
| FacturaB_COPIA.frm | 9583 | JOIN | "INNER JOIN lote_stock ON (lote.id_lote = lote_stock.id_lote… |
| FacturaB_COPIA.frm | 17478 | SELECT | rs_lotestock.Open "Select * From lote_stock " & _ |
| FacturaB_COPIA.frm | 17538 | SELECT | rs_lote.Open "SELECT * from lote_stock where id_lote_stock=0… |
| FacturaB_COPIA.frm | 17796 | JOIN | "LEFT JOIN lote_stock ON (lote_stock.id_lote = lote.id_lote)… |
| NotaCred_COPIA.frm | 3504 | JOIN | "INNER JOIN lote_stock ON (lote.id_lote = lote_stock.id_lote… |
| NotaCred_COPIA.frm | 12580 | JOIN | "INNER JOIN lote_stock ON (lote.id_lote = lote_stock.id_lote… |
| NotaCred_COPIA.frm | 12602 | JOIN | "INNER JOIN lote_stock ON (lote.id_lote = lote_stock.id_lote… |
| NotaCred_COPIA.frm | 12882 | JOIN | "INNER JOIN lote_stock ON (lote.id_lote = lote_stock.id_lote… |
| NotaCred_COPIA.frm | 12904 | JOIN | "INNER JOIN lote_stock ON (lote.id_lote = lote_stock.id_lote… |
| TPV.frm | 6624 | JOIN | "INNER JOIN lote_stock ON (lote.id_lote = lote_stock.id_lote… |
| TPV.frm | 9723 | JOIN | "INNER JOIN lote_stock ON (lote.id_lote = lote_stock.id_lote… |
| TPV.frm | 13650 | JOIN | '        "INNER JOIN lote_stock ON (lote.id_lote = lote_stoc… |
| TPV.frm | 13656 | JOIN | "INNER JOIN lote_stock ON (lote.id_lote = lote_stock.id_lote… |
| TPV.frm | 15024 | JOIN | "INNER JOIN lote_stock on (lote.id_lote = lote_stock.id_lote… |
| TPV.frm | 35265 | SELECT | rs_lotestock.Open "Select * From lote_stock " & _ |
| TPV.frm | 35325 | SELECT | rs_lote.Open "SELECT * from lote_stock where id_lote_stock=0… |
| TPV.frm | 35625 | JOIN | "LEFT JOIN lote_stock ON (lote_stock.id_lote = lote.id_lote)… |
| TPV.frm | 35978 | JOIN | "INNER JOIN lote_stock ON (lote.id_lote = lote_stock.id_lote… |
| TPV.frm | 36000 | JOIN | "INNER JOIN lote_stock ON (lote.id_lote = lote_stock.id_lote… |
| TPV.frm | 36284 | JOIN | "INNER JOIN lote_stock ON (lote.id_lote = lote_stock.id_lote… |
| TPV.frm | 36306 | JOIN | "INNER JOIN lote_stock ON (lote.id_lote = lote_stock.id_lote… |
| TPV.frm | 40095 | JOIN | '               "INNER JOIN lote_stock ON (lote.id_lote = lo… |
| Logi_Gestion2.frm | 7622 | JOIN | "INNER JOIN lote_stock ON (lote.id_lote = lote_stock.id_lote… |
| Logi_Gestion.frm | 9141 | JOIN | "INNER JOIN lote_stock ON (lote.id_lote = lote_stock.id_lote… |
| CargaArticulo_Original.frm | 12778 | SELECT | rs_lotestock.Open "Select * From lote_stock where id_lote = … |
| ABMArticulo_seleccion.frm | 3951 | JOIN | "INNER JOIN lote_stock on (lote.id_lote = lote_stock.id_lote… |
| ABMArticulo_seleccion.frm | 4127 | JOIN | '                        "INNER JOIN lote_stock on (lote.id_… |
| Articulo.frm | 3426 | JOIN | "INNER JOIN lote_stock on (lote.id_lote = lote_stock.id_lote… |
| Articulo.frm | 3821 | JOIN | "INNER JOIN lote_stock on (lote.id_lote = lote_stock.id_lote… |
| Articulo.frm | 4975 | JOIN | "INNER JOIN lote_stock on (lote.id_lote = lote_stock.id_lote… |
| Articulo.frm | 5342 | JOIN | "INNER JOIN lote_stock on (lote.id_lote = lote_stock.id_lote… |
| Articulo.frm | 8809 | JOIN | "INNER JOIN lote_stock on (lote.id_lote = lote_stock.id_lote… |
| Articulo.frm | 9189 | JOIN | '              "INNER JOIN lote_stock on (lote.id_lote = lot… |
| Articulo.frm | 9485 | JOIN | "INNER JOIN lote_stock on (lote.id_lote = lote_stock.id_lote… |
| Articulo.frm | 9858 | JOIN | "INNER JOIN lote_stock on (lote.id_lote = lote_stock.id_lote… |
| Articulo.frm | 10251 | JOIN | "INNER JOIN lote_stock on (lote.id_lote = lote_stock.id_lote… |
| Articulo.frm | 12100 | JOIN | "INNER JOIN lote_stock on (lote.id_lote = lote_stock.id_lote… |
| Articulo.frm | 13106 | JOIN | "INNER JOIN lote_stock on (lote.id_lote = lote_stock.id_lote… |
| Articulo.frm | 14107 | JOIN | "INNER JOIN lote_stock on (lote.id_lote = lote_stock.id_lote… |
| Articulo.frm | 15110 | JOIN | "INNER JOIN lote_stock on (lote.id_lote = lote_stock.id_lote… |
| Articulo.frm | 16105 | JOIN | "INNER JOIN lote_stock on (lote.id_lote = lote_stock.id_lote… |
| Stock_Control.frm | 2716 | JOIN | "LEFT JOIN lote_stock ON (lote_stock.id_lote = lote.id_lote)… |
| Visualiza_FB_Copia.frm | 5385 | JOIN | "INNER JOIN lote_stock ON (lote.id_lote = lote_stock.id_lote… |
| PRemito.frm | 3857 | SELECT | rs_lotestock.Open "Select * From lote_stock where id_lote = … |
| PRemito.frm | 3916 | SELECT | rs_lote.Open "SELECT * from lote_stock where id_lote_stock=0… |
| Visualiza_PNotaCredDev.frm | 2809 | SELECT | rs_lote.Open "SELECT * from lote_stock where id_lote = " & C… |
| Visualiza_PNotaCredDev.frm | 2849 | SELECT | rs_lote.Open "SELECT * from lote_stock where id_lote = " & i… |
| Lista_Pedidos_OPT.frm | 1649 | JOIN | "LEFT JOIN lote_stock ON (lote_stock.id_lote = lote.id_lote)… |
| Lista_Pedidos_OPT.frm | 3069 | JOIN | "INNER JOIN lote_stock on (lote.id_lote = lote_stock.id_lote… |
| Lista_Pedidos_OPT.frm | 3314 | JOIN | "INNER JOIN lote_stock on (lote.id_lote = lote_stock.id_lote… |
| FacturaB.frm | 5858 | JOIN | "INNER JOIN lote_stock ON (lote.id_lote = lote_stock.id_lote… |
| FacturaB.frm | 5926 | JOIN | "INNER JOIN lote_stock ON (lote.id_lote = lote_stock.id_lote… |
| FacturaB.frm | 8689 | JOIN | "INNER JOIN lote_stock ON (lote.id_lote = lote_stock.id_lote… |
| FacturaB.frm | 8757 | JOIN | "INNER JOIN lote_stock ON (lote.id_lote = lote_stock.id_lote… |
| FacturaB.frm | 14993 | JOIN | '        "INNER JOIN lote_stock ON (lote.id_lote = lote_stoc… |
| FacturaB.frm | 15007 | JOIN | "INNER JOIN lote_stock ON (lote.id_lote = lote_stock.id_lote… |
| FacturaB.frm | 15019 | JOIN | "INNER JOIN lote_stock on (lote.id_lote = lote_stock.id_lote… |
| FacturaB.frm | 24132 | SELECT | rs_lotestock.Open "Select * From lote_stock " & _ |
| FacturaB.frm | 24192 | SELECT | rs_lote.Open "SELECT * from lote_stock where id_lote_stock=0… |
| FacturaB.frm | 24541 | JOIN | "LEFT JOIN lote_stock ON (lote_stock.id_lote = lote.id_lote)… |
| NotaCred_SinCompO.frm | 4354 | JOIN | "INNER JOIN lote_stock ON (lote.id_lote = lote_stock.id_lote… |
| NotaCred_SinCompO.frm | 7522 | JOIN | '        "INNER JOIN lote_stock ON (lote.id_lote = lote_stoc… |
| NotaCred_SinCompO.frm | 9207 | JOIN | "INNER JOIN lote_stock ON (lote.id_lote = lote_stock.id_lote… |
| NotaCred_SinCompO.frm | 15030 | JOIN | "INNER JOIN lote_stock ON (lote.id_lote = lote_stock.id_lote… |
| NotaCred_SinCompO.frm | 15060 | JOIN | "INNER JOIN lote_stock ON (lote.id_lote = lote_stock.id_lote… |
| FacturaA.frm | 5560 | JOIN | "INNER JOIN lote_stock ON (lote.id_lote = lote_stock.id_lote… |
| FacturaA.frm | 5620 | JOIN | "INNER JOIN lote_stock ON (lote.id_lote = lote_stock.id_lote… |
| FacturaA.frm | 10723 | JOIN | "INNER JOIN lote_stock ON (lote.id_lote = lote_stock.id_lote… |
| FacturaA.frm | 10735 | JOIN | "INNER JOIN lote_stock on (lote.id_lote = lote_stock.id_lote… |
| … | … | … | *(160 referencias más)* |

---

## 4. Uso en Synap (reports)

*No se encontraron referencias en el módulo reports.*

[← Índice de tablas](../DB_INDICE_TABLAS.md)