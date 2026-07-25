# Tabla `op_factura`

Base: **administranet**

---

## 1. Schema (information_schema)

### 1.1 Columnas

| Campo | Tipo | Nulo | PK | FK | Referencia |
|-------|------|------|----|----|------------|
| Fecha | DATE | Sí |  |  |  |
| TipoComprobante | VARCHAR | Sí |  |  |  |
| NroComprobante | VARCHAR | Sí |  |  |  |
| Importe | DECIMAL | Sí |  |  |  |
| ImporteNC | DECIMAL | Sí |  |  |  |
| Cancelado | DECIMAL | Sí |  |  |  |
| Saldo | DECIMAL | Sí |  |  |  |
| Neto | DECIMAL | Sí |  |  |  |
| Codigo | VARCHAR | Sí |  |  |  |
| CodigoMovimiento | DECIMAL | Sí |  |  |  |
| Vencimiento | DATE | Sí |  |  |  |
| CondCompra | VARCHAR | Sí |  |  |  |
| Anulado | VARCHAR | Sí |  |  |  |
| Estado | VARCHAR | Sí |  |  |  |
| Modificado | VARCHAR | Sí |  |  |  |
| Imp | VARCHAR | Sí |  |  |  |
| OP | VARCHAR | Sí |  |  |  |
| OPMov | DECIMAL | Sí |  |  |  |
| Seleccionado | VARCHAR | Sí |  |  |  |
| Tipo | VARCHAR | Sí |  |  |  |
| id_asig_pago | DECIMAL | Sí |  |  |  |
| id_op_factura | DOUBLE | No | ✓ |  |  |
| id_proyecto | INT | Sí |  |  |  |
| desimputado | VARCHAR | Sí |  |  |  |
| fecha_registro | DATE | Sí |  |  |  |
| fecha_recepcion | DATE | Sí |  |  |  |

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
| PNotaCred.frm | 3438 | SELECT | rs_factura_imputar.Open "SELECT * FROM op_factura where Codi… |
| PNotaCred.frm | 3443 | SELECT | rs_consulta_nc.Open "SELECT * FROM op_factura WHERE CodigoMo… |
| PNotaCred.frm | 3546 | SELECT | rs_op_factura.Open "SELECT * FROM op_factura where CodigoMov… |
| PNotaCred.frm | 3598 | SELECT | rs_op_factura.Open "SELECT * FROM op_factura where CodigoMov… |
| PNotaCred.frm | 3643 | SELECT | rs_factura_imputar.Open "SELECT * FROM op_factura where Codi… |
| PNotaCred.frm | 3674 | SELECT | '                    rs_factura_imputar.Open "SELECT * FROM … |
| PNotaCred.frm | 3680 | SELECT | '                    rs_factura_imputar.Open "SELECT * FROM … |
| PNotaCred.frm | 3685 | SELECT | '                        rs_consulta_nc.Open "SELECT * FROM … |
| PNotaCred.frm | 3689 | SELECT | '                            rs_consulta_nc.Open "SELECT * F… |
| PNotaCred.frm | 3784 | SELECT | '                        rs_op_factura.Open "SELECT * FROM o… |
| PNotaCred.frm | 3836 | SELECT | '                        rs_op_factura.Open "SELECT * FROM o… |
| PNotaCred.frm | 6013 | SELECT | rs_RecFact.Open "SELECT * from op_factura where CodigoMovimi… |
| Info_Estadistica.frm | 4121 | SELECT | "Set reporte_flujofondos_temp.imp_pagos = (SELECT sum(op_fac… |
| Visualiza_PNotaDeb.frm | 2925 | SELECT | rs_RecFact.Open "SELECT * from op_factura where CodigoMovimi… |
| OrdenPago.frm | 7339 | SELECT | rs_op_factura.Open "SELECT * FROM op_factura where CodigoMov… |
| OrdenPago.frm | 7384 | SELECT | rs_op_factura.Open "SELECT * FROM op_factura where CodigoMov… |
| OrdenPago.frm | 7479 | SELECT | rs_op_factura.Open "SELECT * FROM op_factura where CodigoMov… |
| OrdenPago.frm | 9595 | SELECT | .Source = "select * from op_factura where " & _ |
| OrdenPago.frm | 9615 | SELECT | .Source = "select * from op_factura where " & _ |
| OrdenPago.frm | 10009 | SELECT | " FROM op_factura " & _ |
| OrdenPago.frm | 10035 | SELECT | " FROM op_factura " & _ |
| OrdenPago.frm | 10145 | SELECT | .Source = "SELECT Codigo,Estado,Saldo,TipoComprobante,Anulad… |
| OrdenPago.frm | 11632 | SELECT | rs_consulta_ret_ganancia.Open "SELECT SUM(op_factura.Neto) A… |
| OrdenPago.frm | 11879 | SELECT | rs_consulta_ret_ganancia.Open "SELECT SUM(op_factura.Neto) A… |
| OrdenPago.frm | 12014 | SELECT | rs_consultaH.Open "SELECT SUM(op_factura.Neto) AS SumaNeto F… |
| OrdenPago.frm | 16546 | SELECT | " FROM op_factura " & _ |
| OrdenPago.frm | 16572 | SELECT | " FROM op_factura " & _ |
| OrdenPago.frm | 16650 | SELECT | .Source = "SELECT Codigo,Estado,Saldo,TipoComprobante,Anulad… |
| AsigPagoD.frm | 881 | SELECT | data_imputacion_fact.RecordSource = "SELECT * FROM op_factur… |
| AsigPagoD.frm | 1004 | SELECT | rs_op_factura.Open "SELECT * FROM op_factura WHERE " & _ |
| AsigPagoD.frm | 1095 | SELECT | rs_op_factura_acuenta.Open "SELECT * FROM op_factura WHERE "… |
| AsigPagoD.frm | 1129 | SELECT | rs_op_factura_acuenta_nuevo.Open "SELECT * FROM op_factura W… |
| AsigPagoD.frm | 1176 | SELECT | rs_op_factura_acuenta_nuevo.Open "SELECT * FROM op_factura W… |
| AsigPagoD.frm | 1236 | SELECT | data_imputacion_fact.RecordSource = "SELECT * FROM op_factur… |
| AsigPagoD.frm | 1284 | SELECT | data_imputacion_fact.RecordSource = "SELECT * FROM op_factur… |
| Visualiza_PNotaCred_Importe.frm | 2301 | SELECT | rs_factura_imputar.Open "SELECT * FROM op_factura where Codi… |
| Visualiza_PNotaCred_Importe.frm | 2306 | SELECT | rs_consulta_nc.Open "SELECT * FROM op_factura WHERE CodigoMo… |
| Visualiza_PNotaCred_Importe.frm | 2365 | SELECT | rs_op_factura.Open "SELECT * FROM op_factura where CodigoMov… |
| Visualiza_PNotaCred_Importe.frm | 2417 | SELECT | rs_op_factura.Open "SELECT * FROM op_factura where CodigoMov… |
| Visualiza_PNotaCred_Importe.frm | 2470 | SELECT | rs_op_factura.Open "SELECT * FROM op_factura where CodigoMov… |
| Visualiza_PNotaCred_Importe.frm | 3018 | SELECT | rs_RecFact.Open "SELECT * from op_factura where CodigoMovimi… |
| Visualiza_PNotaCredDev.frm | 2969 | SELECT | rs_factura_imputar.Open "SELECT * FROM op_factura where Codi… |
| Visualiza_PNotaCredDev.frm | 2974 | SELECT | rs_consulta_nc.Open "SELECT * FROM op_factura WHERE CodigoMo… |
| Visualiza_PNotaCredDev.frm | 3069 | SELECT | rs_op_factura.Open "SELECT * FROM op_factura where CodigoMov… |
| Visualiza_PNotaCredDev.frm | 3121 | SELECT | rs_op_factura.Open "SELECT * FROM op_factura where CodigoMov… |
| Visualiza_PNotaCredDev.frm | 4770 | SELECT | rs_RecFact.Open "SELECT * from op_factura where CodigoMovimi… |
| Visualiza_PNotaCredDesc.frm | 2543 | SELECT | rs_RecFact.Open "SELECT * from op_factura where CodigoMovimi… |
| PNotaDebCopia.frm | 2071 | SELECT | rs_op_factura.Open "SELECT * FROM op_factura where CodigoMov… |
| PNotaDebCopia.frm | 3279 | SELECT | rs_RecFact.Open "SELECT * from op_factura where CodigoMovimi… |
| AsigPago.frm | 900 | SELECT | .Source = "SELECT * FROM op_factura WHERE " & _ |
| AsigPago.frm | 968 | SELECT | .Source = "SELECT * FROM op_factura WHERE " & _ |
| AsigPago.frm | 1165 | SELECT | rs_op_factura.Open "SELECT * FROM op_factura WHERE id_op_fac… |
| AsigPago.frm | 1192 | SELECT | rs_op_factura.Open "SELECT * FROM op_factura WHERE id_op_fac… |
| Visualiza_PNotaCred_ImporteCopia.frm | 2166 | SELECT | rs_factura_imputar.Open "SELECT * FROM op_factura where Codi… |
| Visualiza_PNotaCred_ImporteCopia.frm | 2171 | SELECT | rs_consulta_nc.Open "SELECT * FROM op_factura WHERE CodigoMo… |
| Visualiza_PNotaCred_ImporteCopia.frm | 2230 | SELECT | rs_op_factura.Open "SELECT * FROM op_factura where CodigoMov… |
| Visualiza_PNotaCred_ImporteCopia.frm | 2282 | SELECT | rs_op_factura.Open "SELECT * FROM op_factura where CodigoMov… |
| Visualiza_PNotaCred_ImporteCopia.frm | 2335 | SELECT | rs_op_factura.Open "SELECT * FROM op_factura where CodigoMov… |
| Visualiza_PNotaCred_ImporteCopia.frm | 2883 | SELECT | rs_RecFact.Open "SELECT * from op_factura where CodigoMovimi… |
| PFactura.frm | 5412 | SELECT | rs_op_factura.Open "SELECT * FROM op_factura WHERE CodigoMov… |
| PFactura.frm | 8466 | SELECT | rs_opfact.Open "SELECT * from op_factura where codigomovimie… |
| ConsultaComprobante.frm | 12383 | SELECT | '            rs_op_factura.Open "SELECT * FROM op_factura WH… |
| ConsultaComprobante.frm | 12397 | SELECT | '            rs_op_factura.Open "SELECT * FROM op_factura WH… |
| ConsultaComprobante.frm | 12529 | SELECT | '                        rs_op_factura.Open "SELECT * FROM o… |
| ConsultaComprobante.frm | 12563 | SELECT | '                rs_op_factura.Open "SELECT * FROM op_factur… |
| ConsultaComprobante.frm | 12661 | SELECT | rs_op_factura.Open "SELECT * FROM op_factura WHERE CodigoMov… |
| ConsultaComprobante.frm | 12694 | SELECT | rs_op_factura.Open "SELECT * FROM op_factura WHERE CodigoMov… |
| ConsultaComprobante.frm | 18847 | SELECT | rs_op_factura.Open "SELECT * FROM op_factura WHERE Anulado =… |
| ConsultaComprobante.frm | 18930 | SELECT | rs_op_factura.Open "SELECT * FROM op_factura WHERE CodigoMov… |
| ConsultaComprobante.frm | 19226 | SELECT | rs_op_factura.Open "SELECT * FROM op_factura WHERE CodigoMov… |
| ConsultaComprobante.frm | 19250 | SELECT | rs_op_factura.Open "SELECT * FROM op_factura WHERE CodigoMov… |
| ConsultaComprobante.frm | 19294 | SELECT | rs_op_factura_nc.Open "SELECT * FROM op_factura WHERE Codigo… |
| ConsultaComprobante.frm | 19310 | SELECT | '                rs_op_factura.Open "SELECT * FROM op_factur… |
| ConsultaComprobante.frm | 19334 | SELECT | '                        rs_op_factura.Open "SELECT * FROM o… |
| ConsultaComprobante.frm | 19387 | SELECT | '                        rs_op_factura_nc.Open "SELECT * FRO… |
| ConsultaComprobante.frm | 19435 | SELECT | '                        rs_op_factura.Open "SELECT * FROM o… |
| ConsultaComprobante.frm | 19451 | SELECT | '                rs_op_factura_nc.Open "SELECT * FROM op_fac… |
| ConsultaComprobante.frm | 19624 | SELECT | '            rs_op_factura.Open "SELECT * FROM op_factura WH… |
| ConsultaComprobante.frm | 19644 | SELECT | rs_op_factura.Open "SELECT * FROM op_factura WHERE Anulado =… |
| ConsultaComprobante.frm | 19733 | SELECT | rs_op_factura.Open "SELECT * FROM op_factura WHERE CodigoMov… |
| … | … | … | *(63 referencias más)* |

---

## 4. Uso en Synap (reports)

*No se encontraron referencias en el módulo reports.*

[← Índice de tablas](../DB_INDICE_TABLAS.md)