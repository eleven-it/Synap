# Tabla `rem_fact`

Base: **administranet**

---

## 1. Schema (information_schema)

### 1.1 Columnas

| Campo | Tipo | Nulo | PK | FK | Referencia |
|-------|------|------|----|----|------------|
| id_rem_fact | DOUBLE | No | ✓ |  |  |
| CodigoMovimientoR | DECIMAL | Sí |  |  |  |
| CodigoMovimientoF | DECIMAL | Sí |  |  |  |
| Anulado | VARCHAR | Sí |  |  |  |

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
| Visualiza_ReciboCobro.frm | 11105 | SELECT | rs_rem_fact.Open "SELECT * FROM rem_fact WHERE CodigoMovimie… |
| Visualiza_ReciboCobro.frm | 11448 | SELECT | rs_rem_fact.Open "SELECT * FROM rem_fact WHERE CodigoMovimie… |
| Visualiza_NotaCred.frm | 6322 | SELECT | rs_rem_fact.Open "SELECT * FROM rem_fact " & _ |
| FacturaB_COPIA.frm | 5171 | SELECT | rs_remito_factura.Open "SELECT * FROM rem_fact WHERE CodigoM… |
| NotaCred_COPIA.frm | 2517 | SELECT | rs_valid_nc_factura.Open "SELECT * FROM rem_fact WHERE Codig… |
| NotaCred_COPIA.frm | 3470 | SELECT | rs_rem_fact.Open "SELECT * FROM rem_fact WHERE CodigoMovimie… |
| NotaCred_COPIA.frm | 4077 | SELECT | rs_rem_fact.Open "SELECT * FROM rem_fact WHERE CodigoMovimie… |
| NotaCred_COPIA.frm | 12209 | SELECT | rs_rem_fact.Open "SELECT * FROM rem_fact " & _ |
| NotaCred_COPIA.frm | 12322 | SELECT | rs_rem_fact.Open "SELECT * FROM rem_fact " & _ |
| Logi_Gestion2.frm | 7357 | SELECT | '    rs_rem_fact.Open "SELECT * FROM rem_fact WHERE CodigoMo… |
| Logi_Gestion.frm | 8876 | SELECT | '    rs_rem_fact.Open "SELECT * FROM rem_fact WHERE CodigoMo… |
| AjustarSaldos.frm | 653 | SELECT | rs_rem_fact.Open "SELECT * FROM rem_fact WHERE CodigoMovimie… |
| trz_trazabilidad.frm | 2348 | JOIN | "LEFT OUTER JOIN rem_fact ON (rem_fact.CodigoMovimientoF = c… |
| trz_trazabilidad.frm | 2374 | JOIN | "LEFT OUTER JOIN rem_fact ON (rem_fact.CodigoMovimientoF = c… |
| trz_trazabilidad.frm | 2430 | JOIN | "LEFT OUTER JOIN rem_fact ON (rem_fact.CodigoMovimientoF = c… |
| trz_trazabilidad.frm | 2445 | JOIN | "LEFT OUTER JOIN rem_fact ON (rem_fact.CodigoMovimientoF = c… |
| trz_trazabilidad.frm | 2461 | JOIN | "LEFT OUTER JOIN rem_fact ON (rem_fact.CodigoMovimientoF = c… |
| trz_trazabilidad.frm | 2665 | JOIN | "RIGHT OUTER JOIN rem_fact ON (rem_fact.CodigoMovimientoF= p… |
| trz_trazabilidad.frm | 2683 | JOIN | "RIGHT OUTER JOIN rem_fact ON (rem_fact.CodigoMovimientoR = … |
| trz_trazabilidad.frm | 2705 | JOIN | "RIGHT OUTER JOIN rem_fact ON (rem_fact.CodigoMovimientoR = … |
| trz_trazabilidad.frm | 2723 | JOIN | "RIGHT OUTER JOIN rem_fact ON (rem_fact.CodigoMovimientoR = … |
| trz_trazabilidad.frm | 2938 | JOIN | "RIGHT OUTER JOIN rem_fact ON (rem_fact.CodigoMovimientoF= p… |
| trz_trazabilidad.frm | 2956 | JOIN | "RIGHT OUTER JOIN rem_fact ON (rem_fact.CodigoMovimientoR = … |
| trz_trazabilidad.frm | 2977 | JOIN | "RIGHT OUTER JOIN rem_fact ON (rem_fact.CodigoMovimientoR = … |
| trz_trazabilidad.frm | 2994 | JOIN | "RIGHT OUTER JOIN rem_fact ON (rem_fact.CodigoMovimientoR = … |
| trz_trazabilidad.frm | 3025 | JOIN | '                                 "LEFT OUTER JOIN rem_fact … |
| trz_trazabilidad.frm | 3144 | JOIN | "RIGHT OUTER JOIN rem_fact ON (rem_fact.CodigoMovimientoR = … |
| trz_trazabilidad.frm | 3162 | JOIN | "RIGHT OUTER JOIN rem_fact ON (rem_fact.CodigoMovimientoR = … |
| trz_trazabilidad.frm | 3181 | JOIN | "RIGHT OUTER JOIN rem_fact ON (rem_fact.CodigoMovimientoR = … |
| trz_trazabilidad.frm | 3201 | JOIN | "RIGHT OUTER JOIN rem_fact ON (rem_fact.CodigoMovimientoR = … |
| trz_trazabilidad.frm | 3221 | JOIN | "RIGHT OUTER JOIN rem_fact ON (rem_fact.CodigoMovimientoR = … |
| trz_trazabilidad.frm | 3290 | JOIN | "RIGHT OUTER JOIN rem_fact ON (rem_fact.CodigoMovimientoF = … |
| trz_trazabilidad.frm | 3323 | JOIN | "LEFT OUTER JOIN rem_fact ON (rem_fact.CodigoMovimientoF = f… |
| trz_trazabilidad.frm | 3412 | JOIN | "RIGHT OUTER JOIN rem_fact ON (rem_fact.CodigoMovimientoF = … |
| trz_trazabilidad.frm | 3445 | JOIN | "LEFT OUTER JOIN rem_fact ON (rem_fact.CodigoMovimientoF = f… |
| trz_trazabilidad.frm | 3535 | JOIN | "RIGHT OUTER JOIN rem_fact ON (rem_fact.CodigoMovimientoF = … |
| trz_trazabilidad.frm | 3568 | JOIN | "LEFT OUTER JOIN rem_fact ON (rem_fact.CodigoMovimientoF = f… |
| trz_trazabilidad.frm | 3886 | SELECT | '            rs_rem_fact.Open "SELECT * FROM rem_fact WHERE … |
| trz_trazabilidad.frm | 4296 | SELECT | '            rs_rem_fact.Open "SELECT * FROM rem_fact WHERE … |
| Visualiza_FB_Copia.frm | 8067 | SELECT | "FROM rem_fact " & _ |
| FacturaB.frm | 6314 | SELECT | rs_remito_factura.Open "SELECT * FROM rem_fact WHERE CodigoM… |
| FacturaB.frm | 9145 | SELECT | rs_remito_factura.Open "SELECT * FROM rem_fact WHERE CodigoM… |
| NotaCred_SinCompO.frm | 3222 | SELECT | '        rs_valid_nc_factura.Open "SELECT * FROM rem_fact WH… |
| NotaCred_SinCompO.frm | 5049 | SELECT | rs_rem_fact.Open "SELECT * FROM rem_fact WHERE CodigoMovimie… |
| NotaCred_SinCompO.frm | 14519 | SELECT | rs_rem_fact.Open "SELECT * FROM rem_fact " & _ |
| NotaCred_SinCompO.frm | 14633 | SELECT | rs_rem_fact.Open "SELECT * FROM rem_fact " & _ |
| FacturaA.frm | 6031 | SELECT | rs_remito_factura.Open "SELECT * FROM rem_fact WHERE CodigoM… |
| PNotaDebCopia.frm | 5086 | SELECT | '                            rs_rem_fact.Open "SELECT * FROM… |
| Visualiza_FA.frm | 7912 | SELECT | "FROM rem_fact " & _ |
| NotaCredCopia.frm | 2742 | SELECT | rs_valid_nc_factura.Open "SELECT * FROM rem_fact WHERE Codig… |
| NotaCredCopia.frm | 2867 | SELECT | '        rs_valid_nc_factura.Open "SELECT * FROM rem_fact WH… |
| NotaCredCopia.frm | 4013 | SELECT | rs_rem_fact.Open "SELECT * FROM rem_fact WHERE CodigoMovimie… |
| NotaCredCopia.frm | 4651 | SELECT | rs_rem_fact.Open "SELECT * FROM rem_fact WHERE CodigoMovimie… |
| NotaCredCopia.frm | 13384 | SELECT | rs_rem_fact.Open "SELECT * FROM rem_fact " & _ |
| NotaCredCopia.frm | 13497 | SELECT | rs_rem_fact.Open "SELECT * FROM rem_fact " & _ |
| Remito.frm | 5150 | SELECT | rs_rem_fact.Open "SELECT * FROM rem_fact WHERE id_rem_fact =… |
| Visualiza_FB.frm | 8602 | SELECT | "FROM rem_fact " & _ |
| ConsultaComprobante.frm | 5922 | SELECT | rs_consulta_remito.Open "SELECT * FROM rem_fact WHERE Anulad… |
| ConsultaComprobante.frm | 6371 | SELECT | rs_rem_fact.Open "SELECT * FROM rem_fact WHERE CodigoMovimie… |
| ConsultaComprobante.frm | 6910 | SELECT | rs_rem_fact.Open "SELECT * FROM rem_fact WHERE CodigoMovimie… |
| ConsultaComprobante.frm | 7500 | SELECT | '            rs_consulta_remito.Open "SELECT * FROM rem_fact… |
| ConsultaComprobante.frm | 7932 | SELECT | '        rs_rem_fact.Open "SELECT * FROM rem_fact WHERE Codi… |
| ConsultaComprobante.frm | 8373 | SELECT | '                        rs_rem_fact.Open "SELECT * FROM rem… |
| ConsultaComprobante.frm | 17341 | SELECT | '            rs_rem_fact.Open "SELECT * FROM rem_fact WHERE … |
| ConsultaComprobante.frm | 18281 | SELECT | '            rs_rem_fact.Open "SELECT * FROM rem_fact WHERE … |
| ConsultaComprobante.frm | 20738 | SELECT | rs_rem_fact.Open "SELECT * FROM rem_fact WHERE CodigoMovimie… |
| ConsultaComprobante.frm | 20776 | SELECT | "From rem_fact " & _ |
| ConsultaComprobante.frm | 21098 | SELECT | rs_rem_fact.Open "SELECT * FROM rem_fact WHERE CodigoMovimie… |
| ConsultaComprobante.frm | 32616 | SELECT | '            rs_rem_fact.Open "SELECT * FROM rem_fact WHERE … |
| NotaDeb.frm | 3360 | SELECT | rs_rem_fact.Open "SELECT * FROM rem_fact WHERE CodigoMovimie… |
| trz_trazabilidadComp.frm | 2865 | JOIN | '#LEFT OUTER JOIN rem_fact ON (rem_fact.CodigoMovimientoF = … |
| trz_trazabilidadComp.frm | 2982 | JOIN | '    #LEFT OUTER JOIN rem_fact ON (rem_fact.CodigoMovimiento… |
| Visualiza_NotaCredCopia.frm | 6012 | SELECT | rs_rem_fact.Open "SELECT * FROM rem_fact " & _ |
| NotaCred.frm | 2840 | SELECT | rs_valid_nc_factura.Open "SELECT * FROM rem_fact WHERE Codig… |
| NotaCred.frm | 2965 | SELECT | '        rs_valid_nc_factura.Open "SELECT * FROM rem_fact WH… |
| NotaCred.frm | 4107 | SELECT | rs_rem_fact.Open "SELECT * FROM rem_fact WHERE CodigoMovimie… |
| NotaCred.frm | 4794 | SELECT | rs_rem_fact.Open "SELECT * FROM rem_fact WHERE CodigoMovimie… |
| NotaCred.frm | 13977 | SELECT | rs_rem_fact.Open "SELECT * FROM rem_fact " & _ |
| NotaCred.frm | 14090 | SELECT | rs_rem_fact.Open "SELECT * FROM rem_fact " & _ |
| PNotaDeb.frm | 5312 | SELECT | '                            rs_rem_fact.Open "SELECT * FROM… |
| … | … | … | *(14 referencias más)* |

---

## 4. Uso en Synap (reports)

*No se encontraron referencias en el módulo reports.*

[← Índice de tablas](../DB_INDICE_TABLAS.md)