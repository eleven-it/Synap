# Tabla `imputacion`

Base: **administranet**

---

## 1. Schema (information_schema)

### 1.1 Columnas

| Campo | Tipo | Nulo | PK | FK | Referencia |
|-------|------|------|----|----|------------|
| id_imputacion | DOUBLE | No | ✓ |  |  |
| fecha_fac_nd | DATE | Sí |  |  |  |
| tipo_comp_fac_nd | VARCHAR | Sí |  |  |  |
| nro_comp_fac_nd | VARCHAR | Sí |  |  |  |
| codmov_fac_nd | DECIMAL | Sí |  |  |  |
| importe_fac_nd | DECIMAL | Sí |  |  |  |
| importe_cancelado_fac_nd | DECIMAL | Sí |  |  |  |
| importe_saldo_fac_nd | DECIMAL | Sí |  |  |  |
| estado_fac_nd | VARCHAR | Sí |  |  |  |
| fecha_nc_rec | DATE | Sí |  |  |  |
| tipo_comp_nc_rec | VARCHAR | Sí |  |  |  |
| nro_comp_nc_rec | VARCHAR | Sí |  |  |  |
| codmov_nc_rec | DECIMAL | Sí |  |  |  |
| importe_nc_rec | DECIMAL | Sí |  |  |  |
| importe_cancelado_nc_rec | DECIMAL | Sí |  |  |  |
| importe_saldo_nc_rec | DECIMAL | Sí |  |  |  |
| estado_nc_rec | VARCHAR | Sí |  |  |  |
| tipo | VARCHAR | Sí |  |  |  |
| id_imputacion_cobranza | DECIMAL | Sí |  |  |  |
| anulado | VARCHAR | Sí |  |  |  |
| id_usuario | INT | Sí |  |  |  |
| id_cliente | INT | Sí |  |  |  |

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
| Visualiza_ReciboCobro.frm | 6718 | SELECT | rs_imputacion.Open "SELECT * FROM imputacion WHERE id_imputa… |
| Visualiza_ReciboCobro.frm | 12905 | SELECT | '            rs_impu.Open "SELECT * from imputacion where co… |
| Visualiza_NotaCred.frm | 4959 | SELECT | rs_impu.Open "SELECT * from imputacion where codmov_nc_rec =… |
| NotaCredCon.frm | 2910 | SELECT | rs_imputacion.Open "SELECT * FROM imputacion WHERE id_imputa… |
| NotaCredCon.frm | 6561 | SELECT | rs_impu.Open "SELECT * from imputacion where codmov_nc_rec =… |
| FacturaB_COPIA.frm | 10988 | SELECT | rs_impu.Open "SELECT * from imputacion where codmov_nc_rec =… |
| NotaCred_COPIA.frm | 3858 | SELECT | rs_imputacion.Open "SELECT * FROM imputacion WHERE id_imputa… |
| NotaCred_COPIA.frm | 8035 | SELECT | rs_impu.Open "SELECT * from imputacion where codmov_nc_rec =… |
| TPV.frm | 5553 | SELECT | rs_imputacion.Open "SELECT * FROM imputacion WHERE codmov_fa… |
| TPV.frm | 5635 | SELECT | rs_imputacion.Open "SELECT * FROM imputacion WHERE id_imputa… |
| TPV.frm | 6972 | SELECT | rs_imputacion.Open "SELECT * FROM imputacion WHERE id_imputa… |
| TPV.frm | 7148 | SELECT | rs_imputacion.Open "SELECT * FROM imputacion WHERE id_imputa… |
| CuentaCliente.frm | 1062 | SELECT | rs_consulta_imputacion.Open "SELECT * FROM imputacion WHERE … |
| CuentaCliente.frm | 1066 | SELECT | rs_consulta_imputacion.Open "SELECT * FROM imputacion WHERE … |
| trz_trazabilidad.frm | 2516 | SELECT | "From imputacion " & _ |
| trz_trazabilidad.frm | 2759 | SELECT | "From imputacion " & _ |
| trz_trazabilidad.frm | 3045 | SELECT | "From imputacion " & _ |
| trz_trazabilidad.frm | 3635 | SELECT | "From imputacion " & _ |
| Visualiza_FB_Copia.frm | 6322 | SELECT | rs_impu.Open "SELECT * from imputacion where codmov_nc_rec =… |
| FacturaB.frm | 16796 | SELECT | rs_impu.Open "SELECT * from imputacion where codmov_nc_rec =… |
| NotaCred_SinCompO.frm | 4830 | SELECT | ''                rs_imputacion.Open "SELECT * FROM imputaci… |
| NotaCred_SinCompO.frm | 10369 | SELECT | rs_impu.Open "SELECT * from imputacion where codmov_nc_rec =… |
| FacturaA.frm | 12878 | SELECT | rs_impu.Open "SELECT * from imputacion where codmov_nc_rec =… |
| Visualiza_NotaDeb.frm | 3616 | SELECT | rs_impu.Open "SELECT * from imputacion where codmov_nc_rec =… |
| PNotaDebCopia.frm | 4978 | SELECT | '                rs_factura_cons.Open "SELECT * FROM imputac… |
| PNotaDebCopia.frm | 4989 | SELECT | ''                rs_factura_cons.Open "SELECT * FROM imputa… |
| PNotaDebCopia.frm | 4992 | SELECT | '                    rs_imputacion.Open "SELECT * FROM imput… |
| ListadoFacturas.frm | 826 | SELECT | rs_consulta.Open "SELECT * FROM imputacion WHERE codmov_fac_… |
| NotaCred_Importe.frm | 2506 | SELECT | rs_imputacion.Open "SELECT * FROM imputacion WHERE id_imputa… |
| NotaCred_Importe.frm | 6111 | SELECT | rs_impu.Open "SELECT * from imputacion where codmov_nc_rec =… |
| Visualiza_FA.frm | 6160 | SELECT | rs_impu.Open "SELECT * from imputacion where codmov_nc_rec =… |
| NotaCredCopia.frm | 4430 | SELECT | rs_imputacion.Open "SELECT * FROM imputacion WHERE id_imputa… |
| NotaCredCopia.frm | 8883 | SELECT | rs_impu.Open "SELECT * from imputacion where codmov_nc_rec =… |
| Visualiza_NotaCred_Importe.frm | 2831 | SELECT | rs_impu.Open "SELECT * from imputacion where codmov_nc_rec =… |
| Visualiza_FB.frm | 6861 | SELECT | rs_impu.Open "SELECT * from imputacion where codmov_nc_rec =… |
| ConsultaComprobante.frm | 5944 | SELECT | rs_recibo_factura.Open "SELECT * FROM imputacion WHERE anula… |
| ConsultaComprobante.frm | 6690 | SELECT | rs_recibo_factura.Open "SELECT * FROM imputacion WHERE anula… |
| ConsultaComprobante.frm | 7072 | SELECT | rs_consulta_imputacion.Open "SELECT * FROM imputacion WHERE … |
| ConsultaComprobante.frm | 7077 | SELECT | rs_imputacion.Open "SELECT * FROM imputacion WHERE codmov_nc… |
| ConsultaComprobante.frm | 7138 | SELECT | '                                    rs_imputacion_act.Open … |
| ConsultaComprobante.frm | 7160 | SELECT | '                                    rs_imputacion_act.Open … |
| ConsultaComprobante.frm | 7522 | SELECT | '        rs_recibo_factura.Open "SELECT * FROM imputacion WH… |
| ConsultaComprobante.frm | 8153 | SELECT | '            rs_recibo_factura.Open "SELECT * FROM imputacio… |
| ConsultaComprobante.frm | 8522 | SELECT | '                rs_consulta_imputacion.Open "SELECT * FROM … |
| ConsultaComprobante.frm | 8527 | SELECT | '                    rs_imputacion.Open "SELECT * FROM imput… |
| ConsultaComprobante.frm | 8588 | SELECT | ''                                    rs_imputacion_act.Open… |
| ConsultaComprobante.frm | 8610 | SELECT | ''                                    rs_imputacion_act.Open… |
| ConsultaComprobante.frm | 9116 | SELECT | rs_recibo_factura_par.Open "SELECT * FROM imputacion WHERE c… |
| ConsultaComprobante.frm | 9149 | SELECT | rs_recibo_factura_par.Open "SELECT * FROM imputacion WHERE c… |
| ConsultaComprobante.frm | 9170 | SELECT | rs_recibo_factura_par.Open "SELECT * FROM imputacion WHERE c… |
| ConsultaComprobante.frm | 9206 | SELECT | rs_recibo_factura_par.Open "SELECT * FROM imputacion WHERE c… |
| ConsultaComprobante.frm | 9683 | SELECT | rs_recibo_factura.Open "SELECT * FROM imputacion WHERE anula… |
| ConsultaComprobante.frm | 10541 | SELECT | rs_recibo_factura.Open "SELECT * FROM imputacion WHERE anula… |
| ConsultaComprobante.frm | 11502 | SELECT | rs_recibo_factura_par.Open "SELECT * FROM imputacion WHERE c… |
| ConsultaComprobante.frm | 11521 | SELECT | rs_recibo_factura_par.Open "SELECT * FROM imputacion WHERE c… |
| ConsultaComprobante.frm | 11575 | SELECT | rs_imputacion.Open "SELECT * FROM imputacion WHERE codmov_nc… |
| NotaDeb.frm | 3041 | SELECT | " FROM imputacion WHERE codmov_nc_rec = " & CodMovFact & "",… |
| NotaDeb.frm | 3202 | SELECT | rs_factura_cons.Open "SELECT * FROM imputacion where codmov_… |
| NotaDeb.frm | 3213 | SELECT | '                rs_factura_cons.Open "SELECT * FROM imputac… |
| NotaDeb.frm | 3216 | SELECT | rs_imputacion.Open "SELECT * FROM imputacion WHERE id_imputa… |
| NotaDeb.frm | 7206 | SELECT | rs_impu.Open "SELECT * from imputacion where codmov_nc_rec =… |
| AsigCobranzaD.frm | 1016 | SELECT | rs_validacion.Open "SELECT * FROM imputacion WHERE " & _ |
| AsigCobranzaD.frm | 1057 | SELECT | rs_imputacion_consulta.Open "SELECT * FROM imputacion WHERE … |
| AsigCobranzaD.frm | 1133 | SELECT | rs_imputacion.Open "SELECT * FROM imputacion WHERE " & _ |
| AsigCobranzaD.frm | 1151 | SELECT | rs_imputacion_consulta.Open "SELECT * FROM imputacion WHERE … |
| AsigCobranzaD.frm | 1177 | SELECT | rs_recibo_factura_acuenta.Open "SELECT * FROM imputacion WHE… |
| AsigCobranzaD.frm | 1224 | SELECT | rs_recibo_factura_acuenta.Open "SELECT * FROM imputacion WHE… |
| AsigCobranzaD.frm | 1272 | SELECT | '             rs_recibo_factura_acuenta.Open "SELECT * FROM … |
| AsigCobranzaD.frm | 1308 | SELECT | '        rs_imputacion_consulta.Open "SELECT * FROM imputaci… |
| AsigCobranzaD.frm | 1361 | SELECT | '            rs_recibo_factura_acuenta.Open "SELECT * FROM i… |
| AsigCobranzaD.frm | 1412 | SELECT | '        rs_recibo_factura_acuenta.Open "SELECT * FROM imput… |
| AsigCobranzaD.frm | 1514 | SELECT | 'data_imputacion_rec_nc.RecordSource = "SELECT * FROM imputa… |
| AsigCobranzaD.frm | 1519 | SELECT | data_imputacion_rec_nc.RecordSource = "SELECT * FROM imputac… |
| AsigCobranzaD.frm | 1576 | SELECT | '    data_imputacion_rec_nc.RecordSource = "SELECT * FROM im… |
| AsigCobranzaD.frm | 1582 | SELECT | data_imputacion_rec_nc.RecordSource = "SELECT * FROM imputac… |
| Visualiza_NotaCredCopia.frm | 4645 | SELECT | rs_impu.Open "SELECT * from imputacion where codmov_nc_rec =… |
| NotaCred.frm | 4574 | SELECT | rs_imputacion.Open "SELECT * FROM imputacion WHERE id_imputa… |
| NotaCred.frm | 9467 | SELECT | rs_impu.Open "SELECT * from imputacion where codmov_nc_rec =… |
| Lista_Comp_Gral.frm | 9328 | SELECT | rs_valid_ingreso_comp.Open "SELECT * FROM imputacion WHERE c… |
| Lista_Comp_Gral.frm | 9802 | SELECT | rs_valid_ingreso_comp.Open "SELECT * FROM imputacion WHERE c… |
| … | … | … | *(19 referencias más)* |

---

## 4. Uso en Synap (reports)

*No se encontraron referencias en el módulo reports.*

[← Índice de tablas](../DB_INDICE_TABLAS.md)