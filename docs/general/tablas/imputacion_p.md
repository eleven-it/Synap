# Tabla `imputacion_p`

Base: **administranet**

---

## 1. Schema (information_schema)

### 1.1 Columnas

| Campo | Tipo | Nulo | PK | FK | Referencia |
|-------|------|------|----|----|------------|
| id_imputacion_p | DOUBLE | No | ✓ |  |  |
| fecha_fac_nd | DATE | Sí |  |  |  |
| tipo_comp_fac_nd | VARCHAR | Sí |  |  |  |
| nro_comp_fac_nd | VARCHAR | Sí |  |  |  |
| codmov_fac_nd | DECIMAL | Sí |  |  |  |
| importe_fac_nd | DECIMAL | Sí |  |  |  |
| importe_cancelado_fac_nd | DECIMAL | Sí |  |  |  |
| importe_saldo_fac_nd | DECIMAL | Sí |  |  |  |
| estado_fac_nd | VARCHAR | Sí |  |  |  |
| fecha_nc_op | DATE | Sí |  |  |  |
| tipo_comp_nc_op | VARCHAR | Sí |  |  |  |
| nro_comp_nc_op | VARCHAR | Sí |  |  |  |
| codmov_nc_op | DECIMAL | Sí |  |  |  |
| importe_nc_op | DECIMAL | Sí |  |  |  |
| importe_cancelado_nc_op | DECIMAL | Sí |  |  |  |
| importe_saldo_nc_op | DECIMAL | Sí |  |  |  |
| estado_nc_op | VARCHAR | Sí |  |  |  |
| tipo | VARCHAR | Sí |  |  |  |
| id_imputacion_pago | DECIMAL | Sí |  |  |  |
| anulado | VARCHAR | Sí |  |  |  |
| id_usuario | INT | Sí |  |  |  |
| id_proveedor | INT | Sí |  |  |  |

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
| PNotaCred.frm | 3497 | SELECT | rs_imputacion.Open "SELECT * FROM imputacion_p WHERE id_impu… |
| PNotaCred.frm | 3754 | SELECT | '                            rs_imputacion.Open "SELECT * FR… |
| PNotaCred.frm | 6028 | SELECT | rs_impu.Open "SELECT * from imputacion_p where codmov_nc_op … |
| Visualiza_PNotaDeb.frm | 2940 | SELECT | rs_impu.Open "SELECT * from imputacion_p where codmov_nc_op … |
| OrdenPago.frm | 7350 | SELECT | rs_imputacion.Open "SELECT * FROM imputacion_p WHERE id_impu… |
| AsigPagoD.frm | 1010 | SELECT | rs_imputacion_consulta.Open "SELECT * FROM imputacion_p WHER… |
| AsigPagoD.frm | 1083 | SELECT | rs_imputacion.Open "SELECT * FROM imputacion_p WHERE " & _ |
| AsigPagoD.frm | 1101 | SELECT | rs_imputacion_consulta.Open "SELECT * FROM imputacion_p WHER… |
| AsigPagoD.frm | 1124 | SELECT | rs_op_factura_acuenta.Open "SELECT * FROM imputacion_p WHERE… |
| AsigPagoD.frm | 1170 | SELECT | rs_op_factura_acuenta.Open "SELECT * FROM imputacion_p WHERE… |
| AsigPagoD.frm | 1270 | SELECT | data_imputacion_op_nc.RecordSource = "SELECT * FROM imputaci… |
| AsigPagoD.frm | 1275 | SELECT | 'data_imputacion_op_nc.RecordSource = "SELECT * FROM imputac… |
| AsigPagoD.frm | 1394 | SELECT | data_imputacion_op_nc.RecordSource = "SELECT * FROM imputaci… |
| Visualiza_PNotaCred_Importe.frm | 3033 | SELECT | rs_impu.Open "SELECT * from imputacion_p where codmov_nc_op … |
| Info_Banco.frm | 1934 | JOIN | "LEFT JOIN imputacion_p ON (imputacion_p.codmov_nc_op = cheq… |
| Visualiza_PNotaCredDev.frm | 3039 | SELECT | rs_imputacion.Open "SELECT * FROM imputacion_p WHERE id_impu… |
| Visualiza_PNotaCredDev.frm | 4785 | SELECT | rs_impu.Open "SELECT * from imputacion_p where codmov_nc_op … |
| Visualiza_PNotaCredDesc.frm | 2558 | SELECT | rs_impu.Open "SELECT * from imputacion_p where codmov_nc_op … |
| PNotaDebCopia.frm | 3294 | SELECT | rs_impu.Open "SELECT * from imputacion_p where codmov_nc_op … |
| AsigPago.frm | 1221 | SELECT | rs_imputacion.Open "SELECT * FROM imputacion_p WHERE id_impu… |
| Visualiza_PNotaCred_ImporteCopia.frm | 2898 | SELECT | rs_impu.Open "SELECT * from imputacion_p where codmov_nc_op … |
| PFactura.frm | 8508 | SELECT | rs_impu.Open "SELECT * from imputacion_p where codmov_nc_op … |
| ConsultaComprobante.frm | 12502 | SELECT | '                rs_op_factura_par.Open "SELECT * FROM imput… |
| ConsultaComprobante.frm | 12521 | SELECT | '                rs_op_factura_par.Open "SELECT * FROM imput… |
| ConsultaComprobante.frm | 12578 | SELECT | '                rs_imputacion.Open "SELECT * FROM imputacio… |
| ConsultaComprobante.frm | 12634 | SELECT | rs_op_factura_par.Open "SELECT * FROM imputacion_p WHERE cod… |
| ConsultaComprobante.frm | 12653 | SELECT | rs_op_factura_par.Open "SELECT * FROM imputacion_p WHERE cod… |
| ConsultaComprobante.frm | 12709 | SELECT | rs_imputacion.Open "SELECT * FROM imputacion_p WHERE codmov_… |
| ConsultaComprobante.frm | 19181 | SELECT | rs_consulta_imputacion.Open "SELECT * FROM imputacion_p WHER… |
| ConsultaComprobante.frm | 19186 | SELECT | rs_imputacion.Open "SELECT * FROM imputacion_p WHERE codmov_… |
| ConsultaComprobante.frm | 19372 | SELECT | '                         rs_op_factura_par.Open "SELECT * F… |
| ConsultaComprobante.frm | 19406 | SELECT | '                rs_op_factura_par.Open "SELECT * FROM imput… |
| ConsultaComprobante.frm | 19427 | SELECT | '                rs_op_factura_par.Open "SELECT * FROM imput… |
| ConsultaComprobante.frm | 19463 | SELECT | '                rs_op_factura_par.Open "SELECT * FROM imput… |
| ConsultaComprobante.frm | 19831 | SELECT | rs_consulta_imputacion.Open "SELECT * FROM imputacion_p WHER… |
| ConsultaComprobante.frm | 19836 | SELECT | rs_imputacion.Open "SELECT * FROM imputacion_p WHERE codmov_… |
| ConsultaComprobante.frm | 20025 | SELECT | '                        rs_op_factura_par.Open "SELECT * FR… |
| ConsultaComprobante.frm | 20061 | SELECT | '                rs_op_factura_par.Open "SELECT * FROM imput… |
| ConsultaComprobante.frm | 20082 | SELECT | '                rs_op_factura_par.Open "SELECT * FROM imput… |
| ConsultaComprobante.frm | 20118 | SELECT | '                rs_op_factura_par.Open "SELECT * FROM imput… |
| ConsultaComprobante.frm | 20489 | SELECT | rs_op_factura.Open "SELECT * FROM imputacion_p WHERE anulado… |
| ConsultaComprobante.frm | 29900 | SELECT | rs_op_factura.Open "SELECT * FROM imputacion_p WHERE anulado… |
| PNotaCredDesc.frm | 2473 | SELECT | rs_impu.Open "SELECT * from imputacion_p where codmov_nc_op … |
| Visualiza_PFactura_Copia.frm | 6140 | SELECT | rs_impu.Open "SELECT * from imputacion_p where codmov_nc_op … |
| PNotaCred_Importe.frm | 2363 | SELECT | rs_imputacion.Open "SELECT * FROM imputacion_p WHERE id_impu… |
| PNotaCred_Importe.frm | 3323 | SELECT | rs_impu.Open "SELECT * from imputacion_p where codmov_nc_op … |
| Lista_Comp_Gral.frm | 10235 | SELECT | rs_valid_ingreso_comp.Open "SELECT * FROM imputacion_p WHERE… |
| Lista_Comp_Gral.frm | 10484 | SELECT | rs_valid_ingreso_comp.Open "SELECT * FROM imputacion_p WHERE… |
| PNotaDeb.frm | 3500 | SELECT | rs_impu.Open "SELECT * from imputacion_p where codmov_nc_op … |
| PNotaCredCopia.frm | 3412 | SELECT | rs_imputacion.Open "SELECT * FROM imputacion_p WHERE id_impu… |
| PNotaCredCopia.frm | 3669 | SELECT | '                            rs_imputacion.Open "SELECT * FR… |
| PNotaCredCopia.frm | 5732 | SELECT | rs_impu.Open "SELECT * from imputacion_p where codmov_nc_op … |
| Visualiza_PFacturaCopia2.frm | 6279 | SELECT | rs_impu.Open "SELECT * from imputacion_p where codmov_nc_op … |
| Visualiza_PFactura.frm | 6501 | SELECT | rs_impu.Open "SELECT * from imputacion_p where codmov_nc_op … |
| CuentaProveedor.frm | 996 | SELECT | rs_consulta_imputacion.Open "SELECT * FROM imputacion_p WHER… |
| CuentaProveedor.frm | 1000 | SELECT | rs_consulta_imputacion.Open "SELECT * FROM imputacion_p WHER… |
| Visualiza_PNotaCredDevC.frm | 3168 | SELECT | rs_imputacion.Open "SELECT * FROM imputacion_p WHERE id_impu… |
| Visualiza_PNotaCredDevC.frm | 4998 | SELECT | rs_impu.Open "SELECT * from imputacion_p where codmov_nc_op … |
| Detalle_Imputacion.frm | 412 | SELECT | "from imputacion_p WHERE codmov_fac_nd = " & codigo_movimien… |
| Detalle_Imputacion.frm | 422 | SELECT | "from imputacion_p WHERE codmov_fac_nd = " & codigo_movimien… |

---

## 4. Uso en Synap (reports)

*No se encontraron referencias en el módulo reports.*

[← Índice de tablas](../DB_INDICE_TABLAS.md)