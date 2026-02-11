# Tabla `recibo_factura`

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
| Codigo | INT | Sí |  |  |  |
| CodigoMovimiento | DECIMAL | Sí |  |  |  |
| Vencimiento | DATE | Sí |  |  |  |
| CondVenta | VARCHAR | Sí |  |  |  |
| Anulado | VARCHAR | Sí |  |  |  |
| Estado | VARCHAR | Sí |  |  |  |
| Modificado | VARCHAR | Sí |  |  |  |
| Imp | VARCHAR | Sí |  |  |  |
| Recibo | VARCHAR | Sí |  |  |  |
| ReciboMov | DECIMAL | Sí |  |  |  |
| Seleccionado | VARCHAR | Sí |  |  |  |
| Tipo | VARCHAR | Sí |  |  |  |
| CodViajante | INT | Sí |  |  |  |
| id_asig_cobranza | DECIMAL | Sí |  |  |  |
| id_recibo_factura | DOUBLE | No | ✓ |  |  |
| id_proyecto | INT | Sí |  |  |  |
| desimputado | VARCHAR | Sí |  |  |  |

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
| Visualiza_ReciboCobro.frm | 6708 | SELECT | rs_recibo_factura.Open "SELECT * FROM recibo_factura where C… |
| Visualiza_ReciboCobro.frm | 6753 | SELECT | rs_recibo_factura.Open "SELECT * FROM recibo_factura where C… |
| Visualiza_ReciboCobro.frm | 6856 | SELECT | rs_recibo_factura.Open "SELECT * FROM recibo_factura where C… |
| Visualiza_ReciboCobro.frm | 9126 | SELECT | .Source = "SELECT * FROM recibo_factura WHERE " & _ |
| Visualiza_ReciboCobro.frm | 9152 | SELECT | '            .Source = "SELECT * FROM recibo_factura WHERE "… |
| Visualiza_ReciboCobro.frm | 9245 | SELECT | .Source = "SELECT * FROM recibo_factura WHERE " & _ |
| Visualiza_ReciboCobro.frm | 9315 | SELECT | .Source = "SELECT Codigo,Estado,Saldo,TipoComprobante,Anulad… |
| Visualiza_ReciboCobro.frm | 10871 | SELECT | rs_estpv.Open "SELECT recibo_factura.codigomovimiento, cuent… |
| Visualiza_ReciboCobro.frm | 12885 | SELECT | '            rs_RecFact.Open "SELECT * from recibo_factura w… |
| Visualiza_NotaCred.frm | 4944 | SELECT | rs_RecFact.Open "SELECT * from recibo_factura where CodigoMo… |
| Info_Estadistica.frm | 4108 | SELECT | "Set reporte_flujofondos_temp.imp_cobranza = (SELECT sum(rec… |
| NotaCredCon.frm | 1752 | SELECT | rs_consulta.Open "SELECT * FROM recibo_factura WHERE CodigoM… |
| NotaCredCon.frm | 2842 | SELECT | rs_factura_imputar.Open "SELECT * FROM recibo_factura where … |
| NotaCredCon.frm | 2847 | SELECT | rs_consulta_nc.Open "SELECT * FROM recibo_factura WHERE Codi… |
| NotaCredCon.frm | 2957 | SELECT | rs_recibo_factura.Open "SELECT * FROM recibo_factura where C… |
| NotaCredCon.frm | 3012 | SELECT | rs_recibo_factura.Open "SELECT * FROM recibo_factura where C… |
| NotaCredCon.frm | 3060 | SELECT | rs_factura_imputar.Open "SELECT * FROM recibo_factura where … |
| NotaCredCon.frm | 6546 | SELECT | rs_RecFact.Open "SELECT * from recibo_factura where CodigoMo… |
| FacturaB_COPIA.frm | 5014 | SELECT | rs_recibo_factura.Open "SELECT * FROM recibo_factura where C… |
| FacturaB_COPIA.frm | 10958 | SELECT | rs_RecFact.Open "SELECT * from recibo_factura where CodigoMo… |
| NotaCred_COPIA.frm | 2497 | SELECT | '    rs_consulta.Open "SELECT * FROM recibo_factura WHERE Co… |
| NotaCred_COPIA.frm | 3799 | SELECT | rs_factura_imputar.Open "SELECT * FROM recibo_factura where … |
| NotaCred_COPIA.frm | 3804 | SELECT | rs_consulta_nc.Open "SELECT * FROM recibo_factura WHERE Codi… |
| NotaCred_COPIA.frm | 3907 | SELECT | rs_recibo_factura.Open "SELECT * FROM recibo_factura where C… |
| NotaCred_COPIA.frm | 3961 | SELECT | rs_recibo_factura.Open "SELECT * FROM recibo_factura where C… |
| NotaCred_COPIA.frm | 4007 | SELECT | rs_factura_imputar.Open "SELECT * FROM recibo_factura where … |
| NotaCred_COPIA.frm | 4031 | SELECT | '    rs_nc_cancela.Open "SELECT * FROM recibo_factura where … |
| NotaCred_COPIA.frm | 8020 | SELECT | rs_RecFact.Open "SELECT * from recibo_factura where CodigoMo… |
| TPV.frm | 5543 | SELECT | '    rs_recibo_factura.Open "SELECT * FROM recibo_factura wh… |
| TPV.frm | 5606 | SELECT | rs_recibo_factura.Open "SELECT * FROM recibo_factura where C… |
| TPV.frm | 6900 | SELECT | rs_factura_imputar.Open "SELECT * FROM recibo_factura where … |
| TPV.frm | 6907 | SELECT | rs_consulta_nc.Open "SELECT * FROM recibo_factura WHERE Codi… |
| TPV.frm | 7076 | SELECT | rs_factura_imputar.Open "SELECT * FROM recibo_factura where … |
| TPV.frm | 7083 | SELECT | rs_consulta_nc.Open "SELECT * FROM recibo_factura WHERE Codi… |
| TPV.frm | 7263 | SELECT | rs_recibo_factura.Open "SELECT * FROM recibo_factura where C… |
| TPV.frm | 10019 | SELECT | rs_recibo_factura.Open "SELECT * FROM recibo_factura where C… |
| TPV.frm | 40517 | SELECT | rs_recibo_factura.Open "SELECT * FROM recibo_factura where C… |
| CuentaCliente.frm | 1150 | SELECT | rs_recibo_factura.Open "SELECT * FROM recibo_factura WHERE "… |
| CuentaCliente.frm | 3353 | SELECT | rs_recibo_factura.Open "SELECT * FROM recibo_factura where C… |
| CuentaCliente.frm | 3371 | SELECT | rs_recibo_factura.Open "SELECT * FROM recibo_factura where C… |
| Logi_Gestion2.frm | 4578 | SELECT | rs_impuParcial.Open "SELECT * FROM recibo_factura WHERE " & … |
| Logi_Gestion2.frm | 4718 | SELECT | rs_impuParcial.Open "SELECT * FROM recibo_factura WHERE " & … |
| Logi_Gestion2.frm | 6510 | SELECT | '                    DataRecFact.RecordSource = "SELECT * FR… |
| Logi_Gestion2.frm | 7298 | SELECT | '    rs_recibo_factura.Open "SELECT * FROM recibo_factura WH… |
| Logi_Gestion2.frm | 11087 | SELECT | rs_impuParcial.Open "SELECT * FROM recibo_factura WHERE " & … |
| Logi_Gestion2.frm | 11252 | SELECT | '                rs_impuParcial.Open "SELECT * FROM recibo_f… |
| Logi_Gestion.frm | 5614 | SELECT | rs_imputacion_temp.Open "SELECT * FROM recibo_factura WHERE … |
| Logi_Gestion.frm | 5676 | SELECT | ''                rs_impuParcial.Open "SELECT * FROM recibo_… |
| Logi_Gestion.frm | 5683 | SELECT | '                rs_impuParcial.Open "SELECT * FROM recibo_f… |
| Logi_Gestion.frm | 5898 | JOIN | " LEFT JOIN recibo_factura ON (recibo_factura.CodigoMovimien… |
| Logi_Gestion.frm | 5941 | SELECT | rs_impuParcial.Open "SELECT * FROM recibo_factura WHERE " & … |
| Logi_Gestion.frm | 7943 | JOIN | "LEFT JOIN recibo_factura ON (recibo_factura.CodigoMovimient… |
| Logi_Gestion.frm | 7965 | JOIN | "LEFT JOIN recibo_factura ON (recibo_factura.CodigoMovimient… |
| Logi_Gestion.frm | 8817 | SELECT | '    rs_recibo_factura.Open "SELECT * FROM recibo_factura WH… |
| Logi_Gestion.frm | 12082 | SELECT | rs_impuParcial.Open "SELECT * FROM recibo_factura WHERE " & … |
| Logi_Gestion.frm | 12286 | SELECT | '                rs_impuParcial.Open "SELECT * FROM recibo_f… |
| Visualiza_FB_Copia.frm | 6292 | SELECT | rs_RecFact.Open "SELECT * from recibo_factura where CodigoMo… |
| FacturaB.frm | 6157 | SELECT | '                rs_recibo_factura.Open "SELECT * FROM recib… |
| FacturaB.frm | 8988 | SELECT | '                rs_recibo_factura.Open "SELECT * FROM recib… |
| FacturaB.frm | 10028 | SELECT | rs_recibo_factura.Open "SELECT * FROM recibo_factura where C… |
| FacturaB.frm | 16766 | SELECT | rs_RecFact.Open "SELECT * from recibo_factura where CodigoMo… |
| NotaCred_SinCompO.frm | 4771 | SELECT | ''        rs_factura_imputar.Open "SELECT * FROM recibo_fact… |
| NotaCred_SinCompO.frm | 4776 | SELECT | ''            rs_consulta_nc.Open "SELECT * FROM recibo_fact… |
| NotaCred_SinCompO.frm | 4879 | SELECT | '            rs_recibo_factura.Open "SELECT * FROM recibo_fa… |
| NotaCred_SinCompO.frm | 4933 | SELECT | rs_recibo_factura.Open "SELECT * FROM recibo_factura where C… |
| NotaCred_SinCompO.frm | 4979 | SELECT | '            rs_factura_imputar.Open "SELECT * FROM recibo_f… |
| NotaCred_SinCompO.frm | 5003 | SELECT | '    rs_nc_cancela.Open "SELECT * FROM recibo_factura where … |
| NotaCred_SinCompO.frm | 10354 | SELECT | rs_RecFact.Open "SELECT * from recibo_factura where CodigoMo… |
| FacturaA.frm | 5874 | SELECT | rs_recibo_factura.Open "SELECT * FROM recibo_factura where C… |
| FacturaA.frm | 12848 | SELECT | rs_RecFact.Open "SELECT * from recibo_factura where CodigoMo… |
| Visualiza_NotaDeb.frm | 3601 | SELECT | rs_RecFact.Open "SELECT * from recibo_factura where CodigoMo… |
| PNotaDebCopia.frm | 4856 | SELECT | '            rs_consulta_nc.Open "SELECT * FROM recibo_factu… |
| PNotaDebCopia.frm | 4890 | SELECT | '                rs_nc_acuenta.Open "SELECT id_recibo_factur… |
| PNotaDebCopia.frm | 4914 | SELECT | '                    rs_factura_cons.Open "SELECT * FROM rec… |
| PNotaDebCopia.frm | 4930 | SELECT | '                rs_recibo_factura.Open "SELECT * FROM recib… |
| PNotaDebCopia.frm | 4964 | SELECT | '                rs_factura_cons.Open "SELECT * FROM recibo_… |
| NotaCred_Importe.frm | 1263 | SELECT | rs_consulta.Open "SELECT * FROM recibo_factura WHERE CodigoM… |
| NotaCred_Importe.frm | 2438 | SELECT | rs_factura_imputar.Open "SELECT * FROM recibo_factura where … |
| NotaCred_Importe.frm | 2443 | SELECT | rs_consulta_nc.Open "SELECT * FROM recibo_factura WHERE Codi… |
| NotaCred_Importe.frm | 2553 | SELECT | rs_recibo_factura.Open "SELECT * FROM recibo_factura where C… |
| … | … | … | *(144 referencias más)* |

---

## 4. Uso en Synap (reports)

*No se encontraron referencias en el módulo reports.*

[← Índice de tablas](../DB_INDICE_TABLAS.md)