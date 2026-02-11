# Tabla `lote`

Base: **administranet**

---

## 1. Schema (information_schema)

### 1.1 Columnas

| Campo | Tipo | Nulo | PK | FK | Referencia |
|-------|------|------|----|----|------------|
| id_lote | INT | No | ✓ |  |  |
| fecha_vto_lote | DATE | Sí |  |  |  |
| cod_lote | VARCHAR | Sí |  |  |  |
| id_articulo | INT | Sí |  |  |  |
| tipo_lote | VARCHAR | Sí |  |  |  |
| cod_movimiento_entrada | DOUBLE | Sí |  |  |  |
| anulado | VARCHAR | Sí |  |  |  |
| devuelto | VARCHAR | Sí |  |  |  |
| stock_total_lote | DECIMAL | Sí |  |  |  |
| id_proveedor | DOUBLE | Sí |  |  |  |

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
| PNotaCred.frm | 3252 | SELECT | rs_lote_consulta.Open "SELECT * from lote where id_lote = " … |
| PNotaCred.frm | 3274 | SELECT | rs_lote.Open "SELECT * FROM lote WHERE id_lote=" & CuerpoSto… |
| Visualiza_ReciboCobro.frm | 11056 | SELECT | rs_lote.Open "SELECT * FROM lote WHERE id_lote = " & rs_stoc… |
| Visualiza_ReciboCobro.frm | 11178 | SELECT | rs_lote.Open "SELECT * FROM lote WHERE id_lote = " & rs_stoc… |
| Visualiza_ReciboCobro.frm | 11427 | SELECT | rs_lote.Open "SELECT * FROM lote WHERE id_lote = " & rs_stoc… |
| Visualiza_ReciboCobro.frm | 11522 | SELECT | rs_lote.Open "SELECT * FROM lote WHERE id_lote = " & rs_stoc… |
| Visualiza_ReciboCobro.frm | 11774 | SELECT | '                    rs_lote.Open "SELECT * FROM lote WHERE … |
| Visualiza_NotaCred.frm | 3439 | SELECT | '        rs_ConsPorLote.Open "SELECT * From Lote " & _ |
| Visualiza_CargaMovStock.frm | 3059 | SELECT | rs_lote.Open "SELECT * FROM lote WHERE cod_lote = '" & Cuerp… |
| Visualiza_CargaMovStock.frm | 3101 | SELECT | rs_lote.Open "SELECT * FROM lote where id_lote = 0", conn, a… |
| Visualiza_CargaMovStock.frm | 3141 | SELECT | rs_lote.Open "SELECT * From Lote " & _ |
| Visualiza_CargaMovStock.frm | 3677 | SELECT | '        rs_consul.Open "SELECT * FROM lote WHERE cod_lote =… |
| Visualiza_CargaMovStock.frm | 4044 | SELECT | DataLote.RecordSource = "SELECT * FROM lote " & _ |
| Visualiza_CargaMovStock.frm | 4448 | SELECT | DataLote.RecordSource = "SELECT * FROM lote " & _ |
| FacturaB_COPIA.frm | 4722 | SELECT | rs_lote.Open "SELECT * From Lote " & _ |
| FacturaB_COPIA.frm | 4773 | SELECT | rs_lote.Open "SELECT * From Lote " & _ |
| FacturaB_COPIA.frm | 9582 | SELECT | DataLote.RecordSource = "SELECT * From Lote " & _ |
| FacturaB_COPIA.frm | 17465 | SELECT | rs_lote.Open "SELECT * FROM lote " & _ |
| FacturaB_COPIA.frm | 17511 | SELECT | rs_lote.Open "SELECT * FROM lote where id_lote = 0", conn, a… |
| FacturaB_COPIA.frm | 17795 | SELECT | rs_lote.Open "SELECT * FROM lote " & _ |
| NotaCred_COPIA.frm | 3503 | SELECT | rs_lote.Open "SELECT * From Lote " & _ |
| NotaCred_COPIA.frm | 12579 | SELECT | rs_anul_lote.Open "SELECT * From Lote " & _ |
| NotaCred_COPIA.frm | 12601 | SELECT | rs_anul_lote.Open "SELECT * From Lote " & _ |
| NotaCred_COPIA.frm | 12881 | SELECT | rs_anul_lote.Open "SELECT * From Lote " & _ |
| NotaCred_COPIA.frm | 12903 | SELECT | rs_anul_lote.Open "SELECT * From Lote " & _ |
| TPV.frm | 6623 | SELECT | rs_lote.Open "SELECT * From Lote " & _ |
| TPV.frm | 9722 | SELECT | rs_lote.Open "SELECT * From Lote " & _ |
| TPV.frm | 13649 | SELECT | '        TPV_Modifica_Renglon.DataLote.RecordSource = "SELEC… |
| TPV.frm | 13655 | SELECT | TPV_Modifica_Renglon.DataLote.RecordSource = "SELECT * From … |
| TPV.frm | 15023 | SELECT | rs_lot.Open "SELECT * FROM lote " & _ |
| TPV.frm | 35252 | SELECT | rs_lote.Open "SELECT * FROM lote " & _ |
| TPV.frm | 35298 | SELECT | rs_lote.Open "SELECT * FROM lote where id_lote = 0", conn, a… |
| TPV.frm | 35624 | SELECT | rs_lote.Open "SELECT * FROM lote " & _ |
| TPV.frm | 35977 | SELECT | rs_anul_lote.Open "SELECT * From Lote " & _ |
| TPV.frm | 35999 | SELECT | rs_anul_lote.Open "SELECT * From Lote " & _ |
| TPV.frm | 36283 | SELECT | rs_anul_lote.Open "SELECT * From Lote " & _ |
| TPV.frm | 36305 | SELECT | rs_anul_lote.Open "SELECT * From Lote " & _ |
| TPV.frm | 40094 | SELECT | '               rs_lote.Open "SELECT * From Lote " & _ |
| CuentaCliente.frm | 1443 | SELECT | rs_lote.Open "SELECT * FROM lote WHERE id_lote = " & rs_stoc… |
| Logi_Gestion2.frm | 7386 | JOIN | ''            "LEFT JOIN lote ON (lote.id_lote = stock.id_lo… |
| Logi_Gestion2.frm | 7621 | SELECT | rs_lote.Open "SELECT * From Lote " & _ |
| Logi_Gestion2.frm | 9554 | JOIN | "LEFT JOIN lote ON (lote.cod_movimiento_entrada = stockp.cod… |
| Logi_Gestion2.frm | 9582 | JOIN | "LEFT JOIN lote ON (lote.cod_movimiento_entrada = stockp.cod… |
| Logi_Gestion2.frm | 9664 | JOIN | "LEFT JOIN lote ON (lote.cod_movimiento_entrada = stockp.cod… |
| Fito_CargaFecElab.frm | 403 | JOIN | "INNER JOIN lote ON (lote.id_lote = stock.id_lote) " & _ |
| Logi_Gestion.frm | 8905 | JOIN | ''            "LEFT JOIN lote ON (lote.id_lote = stock.id_lo… |
| Logi_Gestion.frm | 9140 | SELECT | rs_lote.Open "SELECT * From Lote " & _ |
| Logi_Gestion.frm | 11207 | JOIN | "LEFT JOIN lote ON (lote.cod_movimiento_entrada = stockp.cod… |
| Logi_Gestion.frm | 11235 | JOIN | "LEFT JOIN lote ON (lote.cod_movimiento_entrada = stockp.cod… |
| Logi_Gestion.frm | 11329 | JOIN | "LEFT JOIN lote ON (lote.cod_movimiento_entrada = stockp.cod… |
| CargaArticulo_Original.frm | 12768 | SELECT | rs_lote.Open "SELECT * FROM lote WHERE cod_lote = '" & rs_ar… |
| OrdenPago.frm | 15283 | SELECT | rs_lote.Open "SELECT * FROM lote WHERE id_lote = " & rs_stoc… |
| OrdenPago.frm | 15358 | SELECT | '                                rs_lote.Open "SELECT * FROM… |
| Fito_Genera.frm | 600 | JOIN | '        "LEFT JOIN lote ON (lote.id_lote = stock.id_lote) "… |
| Fito_Genera.frm | 617 | SELECT | '        data_lote.RecordSource = "SELECT lote.*,lote_stock.… |
| Fito_Genera.frm | 743 | JOIN | "LEFT JOIN lote ON (lote.id_lote = stock.id_lote) " & _ |
| trz_trazabilidad.frm | 3830 | SELECT | rs_lote.Open "SELECT * FROM lote WHERE id_lote = " & rs_stoc… |
| trz_trazabilidad.frm | 3959 | SELECT | '                                    rs_lote.Open "SELECT * … |
| trz_trazabilidad.frm | 4269 | SELECT | rs_lote.Open "SELECT * FROM lote WHERE id_lote = " & rs_stoc… |
| trz_trazabilidad.frm | 4370 | SELECT | '                                    rs_lote.Open "SELECT * … |
| trz_trazabilidad.frm | 4899 | SELECT | rs_lote.Open "SELECT * FROM lote WHERE id_lote = " & rs_stoc… |
| trz_trazabilidad.frm | 5121 | SELECT | '                    rs_lote.Open "SELECT * FROM lote WHERE … |
| trz_trazabilidad.frm | 6036 | SELECT | rs_lote.Open "SELECT * FROM lote WHERE id_lote = " & rs_stoc… |
| ABMArticulo_seleccion.frm | 3534 | SELECT | data_lote.RecordSource = "SELECT lote.*,lote_stock.* FROM lo… |
| ABMArticulo_seleccion.frm | 3543 | SELECT | data_lote.RecordSource = "SELECT lote.*,lote_stock.* FROM lo… |
| ABMArticulo_seleccion.frm | 3950 | SELECT | CargaMovStock.DataLote.RecordSource = "SELECT * FROM lote " … |
| ABMArticulo_seleccion.frm | 4126 | SELECT | '                        En_CargaOE_Art.DataLote.RecordSourc… |
| Articulo.frm | 3425 | SELECT | FacturaA.DataLote.RecordSource = "SELECT * FROM lote " & _ |
| Articulo.frm | 3820 | SELECT | FacturaB.DataLote.RecordSource = "SELECT * FROM lote " & _ |
| Articulo.frm | 4974 | SELECT | Remito.DataLote.RecordSource = "SELECT * FROM lote " & _ |
| Articulo.frm | 5341 | SELECT | Logi_Renglon.DataLote.RecordSource = "SELECT * FROM lote " &… |
| Articulo.frm | 8808 | SELECT | Facturacion_Ciclica_Renglon.DataLote.RecordSource = "SELECT … |
| Articulo.frm | 9188 | SELECT | '              NotaCred.DataLote.RecordSource = "SELECT * FR… |
| Articulo.frm | 9484 | SELECT | NotaCred_SinCompO.DataLote.RecordSource = "SELECT * FROM lot… |
| Articulo.frm | 9857 | SELECT | TPV_Modifica_Renglon.DataLote.RecordSource = "SELECT * FROM … |
| Articulo.frm | 10250 | SELECT | rs_lot.Open "SELECT * FROM lote " & _ |
| Articulo.frm | 12099 | SELECT | rs_lot.Open "SELECT * FROM lote " & _ |
| Articulo.frm | 13105 | SELECT | rs_lot.Open "SELECT * FROM lote " & _ |
| Articulo.frm | 14106 | SELECT | rs_lot.Open "SELECT * FROM lote " & _ |
| Articulo.frm | 15109 | SELECT | rs_lot.Open "SELECT * FROM lote " & _ |
| … | … | … | *(316 referencias más)* |

---

## 4. Uso en Synap (reports)

*No se encontraron referencias en el módulo reports.*

[← Índice de tablas](../DB_INDICE_TABLAS.md)