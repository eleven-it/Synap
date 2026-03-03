# Tabla `recibo_factura_par`

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
| CanceladoActual | DECIMAL | Sí |  |  |  |
| Saldo | DECIMAL | Sí |  |  |  |
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
| Acuenta | DECIMAL | Sí |  |  |  |
| Tipo | VARCHAR | Sí |  |  |  |
| cod | INT | Sí |  |  |  |
| id_asig_cobranza | INT | Sí |  |  |  |
| id_recibo_factura_par | DOUBLE | No | ✓ |  |  |
| id_proyecto | INT | Sí |  |  |  |

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
| Visualiza_ReciboCobro.frm | 6784 | SELECT | rs_recibo_factura_par.Open "SELECT * FROM recibo_factura_par… |
| Visualiza_ReciboCobro.frm | 6824 | SELECT | rs_recibo_factura_par.Open "SELECT * FROM recibo_factura_par… |
| Visualiza_ReciboCobro.frm | 6876 | SELECT | rs_recibo_factura_par.Open "SELECT * FROM recibo_factura_par… |
| NotaCredCon.frm | 2941 | SELECT | rs_factura_imputar.Open "SELECT * FROM recibo_factura_par wh… |
| NotaCredCon.frm | 2985 | SELECT | rs_recibo_factura_par.Open "SELECT * FROM recibo_factura_par… |
| NotaCredCon.frm | 3039 | SELECT | rs_recibo_factura_par.Open "SELECT * FROM recibo_factura_par… |
| FacturaB_COPIA.frm | 10973 | SELECT | rs_RecFactP.Open "SELECT * from recibo_factura_par where Cod… |
| NotaCred_COPIA.frm | 3889 | SELECT | rs_factura_imputar.Open "SELECT * FROM recibo_factura_par wh… |
| NotaCred_COPIA.frm | 3935 | SELECT | rs_recibo_factura_par.Open "SELECT * FROM recibo_factura_par… |
| NotaCred_COPIA.frm | 3984 | SELECT | rs_recibo_factura_par.Open "SELECT * FROM recibo_factura_par… |
| TPV.frm | 7015 | SELECT | rs_factura_imputar.Open "SELECT * FROM recibo_factura_par wh… |
| TPV.frm | 7190 | SELECT | rs_factura_imputar.Open "SELECT * FROM recibo_factura_par wh… |
| TPV.frm | 7284 | SELECT | rs_recibo_factura_par.Open "SELECT * FROM recibo_factura_par… |
| CuentaCliente.frm | 2248 | SELECT | '        rs_recibo_factura_par.Open "SELECT * FROM recibo_fa… |
| CuentaCliente.frm | 3359 | SELECT | rs_recibo_factura_par.Open "SELECT * FROM recibo_factura_par… |
| CuentaCliente.frm | 3377 | SELECT | rs_recibo_factura_par.Open "SELECT * FROM recibo_factura_par… |
| trz_trazabilidad.frm | 7350 | SELECT | rs_recibo_factura_par.Open "SELECT * FROM recibo_factura_par… |
| Visualiza_FB_Copia.frm | 6307 | SELECT | rs_RecFactP.Open "SELECT * from recibo_factura_par where Cod… |
| FacturaB.frm | 16781 | SELECT | rs_RecFactP.Open "SELECT * from recibo_factura_par where Cod… |
| NotaCred_SinCompO.frm | 4861 | SELECT | ''            rs_factura_imputar.Open "SELECT * FROM recibo_… |
| NotaCred_SinCompO.frm | 4908 | SELECT | ''            rs_recibo_factura_par.Open "SELECT * FROM reci… |
| NotaCred_SinCompO.frm | 4956 | SELECT | rs_recibo_factura_par.Open "SELECT * FROM recibo_factura_par… |
| FacturaA.frm | 12863 | SELECT | rs_RecFactP.Open "SELECT * from recibo_factura_par where Cod… |
| NotaCred_Importe.frm | 2537 | SELECT | rs_factura_imputar.Open "SELECT * FROM recibo_factura_par wh… |
| NotaCred_Importe.frm | 2581 | SELECT | rs_recibo_factura_par.Open "SELECT * FROM recibo_factura_par… |
| NotaCred_Importe.frm | 2635 | SELECT | rs_recibo_factura_par.Open "SELECT * FROM recibo_factura_par… |
| Visualiza_FA.frm | 6145 | SELECT | rs_RecFactP.Open "SELECT * from recibo_factura_par where Cod… |
| NotaCredCopia.frm | 4461 | SELECT | rs_factura_imputar.Open "SELECT * FROM recibo_factura_par wh… |
| NotaCredCopia.frm | 4507 | SELECT | rs_recibo_factura_par.Open "SELECT * FROM recibo_factura_par… |
| NotaCredCopia.frm | 4556 | SELECT | rs_recibo_factura_par.Open "SELECT * FROM recibo_factura_par… |
| Sup_importacion_tablas.frm | 9407 | SELECT | rs_recibo_factura_par.Open "SELECT * FROM recibo_factura_par… |
| Sup_importacion_tablas.frm | 9457 | SELECT | rs_recibo_factura_par.Open "SELECT * FROM recibo_factura_par… |
| Visualiza_FB.frm | 6846 | SELECT | rs_RecFactP.Open "SELECT * from recibo_factura_par where Cod… |
| ConsultaComprobante.frm | 6664 | SELECT | rs_recibo_factura_par.Open "SELECT * FROM recibo_factura_par… |
| ConsultaComprobante.frm | 7199 | SELECT | rs_recibo_factura_par.Open "SELECT * FROM recibo_factura_par… |
| ConsultaComprobante.frm | 8127 | SELECT | '                rs_recibo_factura_par.Open "SELECT * FROM r… |
| ConsultaComprobante.frm | 8649 | SELECT | '                    rs_recibo_factura_par.Open "SELECT * FR… |
| ConsultaComprobante.frm | 8872 | SELECT | rs_recibo_factura_par.Open "SELECT * FROM recibo_factura_par… |
| ConsultaComprobante.frm | 9100 | SELECT | rs_recibo_factura_par.Open "SELECT * FROM recibo_factura_par… |
| ConsultaComprobante.frm | 10521 | SELECT | '        rs_recibo_factura.Open "SELECT * FROM recibo_factur… |
| ConsultaComprobante.frm | 11545 | SELECT | rs_recibo_factura_par.Open "SELECT * FROM recibo_factura_par… |
| NotaCred.frm | 4605 | SELECT | rs_factura_imputar.Open "SELECT * FROM recibo_factura_par wh… |
| NotaCred.frm | 4651 | SELECT | rs_recibo_factura_par.Open "SELECT * FROM recibo_factura_par… |
| NotaCred.frm | 4700 | SELECT | rs_recibo_factura_par.Open "SELECT * FROM recibo_factura_par… |
| ReciboCobro.frm | 7240 | SELECT | rs_recibo_factura_par.Open "SELECT * FROM recibo_factura_par… |
| ReciboCobro.frm | 7279 | SELECT | rs_recibo_factura_par.Open "SELECT * FROM recibo_factura_par… |
| ReciboCobro.frm | 7329 | SELECT | rs_recibo_factura_par.Open "SELECT * FROM recibo_factura_par… |
| ReciboCobro.frm | 7377 | SELECT | rs_recibo_factura_par.Open "SELECT * FROM recibo_factura_par… |
| InicSaldos.frm | 968 | SELECT | rs_recibo_factura_par.Open "SELECT * FROM recibo_factura_par… |
| InicSaldos.frm | 1039 | SELECT | rs_recibo_factura_par.Open "SELECT * FROM recibo_factura_par… |
| InicSaldos.frm | 1271 | SELECT | rs_recibo_factura_par.Open "SELECT * FROM recibo_factura_par… |
| InicSaldos.frm | 1332 | SELECT | rs_recibo_factura_par.Open "SELECT * FROM recibo_factura_par… |
| Visualiza_NotaCredCon.frm | 2829 | SELECT | rs_factura_imputar.Open "SELECT * FROM recibo_factura_par wh… |
| Visualiza_NotaCredCon.frm | 2873 | SELECT | rs_recibo_factura_par.Open "SELECT * FROM recibo_factura_par… |
| Visualiza_NotaCredCon.frm | 2927 | SELECT | rs_recibo_factura_par.Open "SELECT * FROM recibo_factura_par… |
| Visualiza_ReciboCobroC.frm | 6550 | SELECT | rs_recibo_factura_par.Open "SELECT * FROM recibo_factura_par… |
| Visualiza_ReciboCobroC.frm | 6590 | SELECT | rs_recibo_factura_par.Open "SELECT * FROM recibo_factura_par… |
| Visualiza_ReciboCobroC.frm | 6642 | SELECT | rs_recibo_factura_par.Open "SELECT * FROM recibo_factura_par… |
| TPV_2.frm | 6436 | SELECT | rs_factura_imputar.Open "SELECT * FROM recibo_factura_par wh… |
| TPV_2.frm | 6496 | SELECT | '                        rs_recibo_factura_par.Open "SELECT … |
| TPV_2.frm | 6594 | SELECT | rs_recibo_factura_par.Open "SELECT * FROM recibo_factura_par… |
| AsigCobranza.frm | 1146 | SELECT | rs_recibo_factura_par.Open "SELECT * FROM recibo_factura_par… |
| Visualiza.bas | 6235 | SELECT | rs_recibo_factura_par.Open "SELECT * FROM recibo_factura_par… |

---

## 4. Uso en Synap (reports)

*No se encontraron referencias en el módulo reports.*

[← Índice de tablas](../DB_INDICE_TABLAS.md)