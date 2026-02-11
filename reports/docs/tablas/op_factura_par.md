# Tabla `op_factura_par`

Base: **administranet**

---

## 1. Schema (information_schema)

### 1.1 Columnas

| Campo | Tipo | Nulo | PK | FK | Referencia |
|-------|------|------|----|----|------------|
| Fecha | DATETIME | Sí |  |  |  |
| TipoComprobante | VARCHAR | Sí |  |  |  |
| NroComprobante | VARCHAR | Sí |  |  |  |
| Importe | DECIMAL | Sí |  |  |  |
| ImporteNC | DECIMAL | Sí |  |  |  |
| Cancelado | DECIMAL | Sí |  |  |  |
| CanceladoActual | DECIMAL | Sí |  |  |  |
| Saldo | DECIMAL | Sí |  |  |  |
| Neto | DECIMAL | Sí |  |  |  |
| Codigo | VARCHAR | Sí |  |  |  |
| CodigoMovimiento | DECIMAL | Sí |  |  |  |
| Vencimiento | DATETIME | Sí |  |  |  |
| CondCompra | VARCHAR | Sí |  |  |  |
| Anulado | VARCHAR | Sí |  |  |  |
| Estado | VARCHAR | Sí |  |  |  |
| Modificado | VARCHAR | Sí |  |  |  |
| Imp | VARCHAR | Sí |  |  |  |
| OP | VARCHAR | Sí |  |  |  |
| OPMov | DECIMAL | Sí |  |  |  |
| Seleccionado | VARCHAR | Sí |  |  |  |
| Acuenta | DECIMAL | Sí |  |  |  |
| Tipo | VARCHAR | Sí |  |  |  |
| cod | INT | Sí |  |  |  |
| id_asig_pago | INT | Sí |  |  |  |
| id_op_factura_par | DOUBLE | No | ✓ |  |  |
| id_proyecto | INT | Sí |  |  |  |
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
| PNotaCred.frm | 3528 | SELECT | rs_factura_imputar.Open "SELECT * FROM op_factura_par where … |
| PNotaCred.frm | 3573 | SELECT | rs_op_factura_par.Open "SELECT * FROM op_factura_par where C… |
| PNotaCred.frm | 3620 | SELECT | rs_op_factura_par.Open "SELECT * FROM op_factura_par where C… |
| PNotaCred.frm | 3738 | SELECT | '                        rs_factura_imputar.Open "SELECT * F… |
| PNotaCred.frm | 3811 | SELECT | '                        rs_op_factura_par.Open "SELECT * FR… |
| PNotaCred.frm | 3856 | SELECT | '                        rs_op_factura_par.Open "SELECT * FR… |
| OrdenPago.frm | 7413 | SELECT | rs_op_factura_par.Open "SELECT * FROM op_factura_par where C… |
| OrdenPago.frm | 7447 | SELECT | rs_op_factura_par.Open "SELECT * FROM op_factura_par where C… |
| OrdenPago.frm | 7503 | SELECT | rs_op_factura_par.Open "SELECT * FROM op_factura_par where C… |
| Visualiza_PNotaCred_Importe.frm | 2349 | SELECT | rs_factura_imputar.Open "SELECT * FROM op_factura_par where … |
| Visualiza_PNotaCred_Importe.frm | 2392 | SELECT | rs_op_factura_par.Open "SELECT * FROM op_factura_par where C… |
| Visualiza_PNotaCred_Importe.frm | 2443 | SELECT | rs_op_factura_par.Open "SELECT * FROM op_factura_par where C… |
| Visualiza_PNotaCred_Importe.frm | 2496 | SELECT | rs_op_factura_par.Open "SELECT * FROM op_factura_par where C… |
| Visualiza_PNotaCredDev.frm | 3023 | SELECT | rs_factura_imputar.Open "SELECT * FROM op_factura_par where … |
| Visualiza_PNotaCredDev.frm | 3096 | SELECT | rs_op_factura_par.Open "SELECT * FROM op_factura_par where C… |
| Visualiza_PNotaCredDev.frm | 3141 | SELECT | rs_op_factura_par.Open "SELECT * FROM op_factura_par where C… |
| PNotaDebCopia.frm | 2109 | SELECT | '        rs_op_factura_par.Open "SELECT * FROM op_factura_pa… |
| AsigPago.frm | 1129 | SELECT | rs_op_factura_par.Open "SELECT * FROM op_factura_par WHERE C… |
| Visualiza_PNotaCred_ImporteCopia.frm | 2214 | SELECT | rs_factura_imputar.Open "SELECT * FROM op_factura_par where … |
| Visualiza_PNotaCred_ImporteCopia.frm | 2257 | SELECT | rs_op_factura_par.Open "SELECT * FROM op_factura_par where C… |
| Visualiza_PNotaCred_ImporteCopia.frm | 2308 | SELECT | rs_op_factura_par.Open "SELECT * FROM op_factura_par where C… |
| Visualiza_PNotaCred_ImporteCopia.frm | 2361 | SELECT | rs_op_factura_par.Open "SELECT * FROM op_factura_par where C… |
| PFactura.frm | 8487 | SELECT | rs_opfactpar.Open "SELECT * from op_factura_par where codigo… |
| ConsultaComprobante.frm | 12548 | SELECT | '                rs_op_factura_par.Open "SELECT * FROM op_fa… |
| ConsultaComprobante.frm | 12678 | SELECT | rs_op_factura_par.Open "SELECT * FROM op_factura_par WHERE O… |
| ConsultaComprobante.frm | 18850 | SELECT | rs_op_factura_par.Open "SELECT * FROM op_factura_par WHERE A… |
| ConsultaComprobante.frm | 19276 | SELECT | rs_op_factura_par.Open "SELECT * FROM op_factura_par WHERE C… |
| ConsultaComprobante.frm | 19356 | SELECT | '                        rs_op_factura_par.Open "SELECT * FR… |
| ConsultaComprobante.frm | 19647 | SELECT | rs_op_factura_par.Open "SELECT * FROM op_factura_par WHERE A… |
| ConsultaComprobante.frm | 19924 | SELECT | rs_op_factura_par.Open "SELECT * FROM op_factura_par WHERE C… |
| ConsultaComprobante.frm | 20009 | SELECT | '                        rs_op_factura_par.Open "SELECT * FR… |
| Visualiza_PFactura_Copia.frm | 6121 | SELECT | rs_opfactpar.Open "SELECT * from op_factura_par where codigo… |
| PNotaCred_Importe.frm | 2394 | SELECT | rs_factura_imputar.Open "SELECT * FROM op_factura_par where … |
| PNotaCred_Importe.frm | 2437 | SELECT | rs_op_factura_par.Open "SELECT * FROM op_factura_par where C… |
| PNotaCred_Importe.frm | 2490 | SELECT | rs_op_factura_par.Open "SELECT * FROM op_factura_par where C… |
| PNotaCred_Importe.frm | 2593 | SELECT | '                            rs_factura_imputar.Open "SELECT… |
| PNotaCred_Importe.frm | 2636 | SELECT | '                            rs_op_factura_par.Open "SELECT … |
| PNotaCred_Importe.frm | 2687 | SELECT | '                            rs_op_factura_par.Open "SELECT … |
| PNotaCred_Importe.frm | 2740 | SELECT | rs_op_factura_par.Open "SELECT * FROM op_factura_par where C… |
| trz_trazabilidadComp.frm | 4806 | SELECT | rs_op_factura_par.Open "SELECT * FROM op_factura_par WHERE O… |
| PNotaDeb.frm | 2203 | SELECT | '        rs_op_factura_par.Open "SELECT * FROM op_factura_pa… |
| PNotaCredCopia.frm | 3443 | SELECT | rs_factura_imputar.Open "SELECT * FROM op_factura_par where … |
| PNotaCredCopia.frm | 3488 | SELECT | rs_op_factura_par.Open "SELECT * FROM op_factura_par where C… |
| PNotaCredCopia.frm | 3535 | SELECT | rs_op_factura_par.Open "SELECT * FROM op_factura_par where C… |
| PNotaCredCopia.frm | 3653 | SELECT | '                        rs_factura_imputar.Open "SELECT * F… |
| PNotaCredCopia.frm | 3726 | SELECT | '                        rs_op_factura_par.Open "SELECT * FR… |
| PNotaCredCopia.frm | 3771 | SELECT | '                        rs_op_factura_par.Open "SELECT * FR… |
| Visualiza_PFacturaCopia2.frm | 6260 | SELECT | rs_opfactpar.Open "SELECT * from op_factura_par where codigo… |
| Visualiza_PFactura.frm | 6478 | SELECT | rs_opfactpar.Open "SELECT * from op_factura_par where codigo… |
| InicSaldos.frm | 1663 | SELECT | rs_op_factura_par.Open "SELECT * FROM op_factura_par where C… |
| InicSaldos.frm | 1733 | SELECT | rs_op_factura_par.Open "SELECT * FROM op_factura_par where C… |
| InicSaldos.frm | 1966 | SELECT | rs_op_factura_par.Open "SELECT * FROM op_factura_par where C… |
| InicSaldos.frm | 2026 | SELECT | rs_op_factura_par.Open "SELECT * FROM op_factura_par where C… |
| CuentaProveedor.frm | 1340 | SELECT | '        rs_op_factura_par.Open "SELECT * FROM op_factura_pa… |
| Visualiza_PNotaCredDevC.frm | 3152 | SELECT | rs_factura_imputar.Open "SELECT * FROM op_factura_par where … |
| Visualiza_PNotaCredDevC.frm | 3225 | SELECT | rs_op_factura_par.Open "SELECT * FROM op_factura_par where C… |
| Visualiza_PNotaCredDevC.frm | 3270 | SELECT | rs_op_factura_par.Open "SELECT * FROM op_factura_par where C… |
| Visualiza.bas | 7453 | SELECT | rs_op_factura_par.Open "SELECT * FROM op_factura_par WHERE O… |

---

## 4. Uso en Synap (reports)

*No se encontraron referencias en el módulo reports.*

[← Índice de tablas](../DB_INDICE_TABLAS.md)