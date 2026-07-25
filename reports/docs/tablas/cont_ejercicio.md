# Tabla `cont_ejercicio`

Base: **administranet**

---

## 1. Schema (information_schema)

### 1.1 Columnas

| Campo | Tipo | Nulo | PK | FK | Referencia |
|-------|------|------|----|----|------------|
| id_ejercicio | DOUBLE | No | ✓ |  |  |
| cerrado | VARCHAR | Sí |  |  |  |
| descripcion_ejercicio | VARCHAR | Sí |  |  |  |
| fecdesde_ejercicio | DATE | Sí |  |  |  |
| fechasta_ejercicio | DATE | Sí |  |  |  |
| activo_ejercicio | VARCHAR | Sí |  |  |  |
| nro_asiento_ejercicio | DOUBLE | No |  |  |  |
| tipo_ejercicio | VARCHAR | Sí |  |  |  |
| id_pc | DOUBLE | Sí |  |  |  |

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
| CargaBDeposito.frm | 2563 | SELECT | rs_ejercicio.Open "Select * from cont_ejercicio where id_eje… |
| CargaBDeposito.frm | 2565 | SELECT | rs_ejercicio.Open "Select * from cont_ejercicio where activo… |
| CargaBDeposito.frm | 2613 | SELECT | rs_nroasiento.Open "select * from cont_ejercicio where id_ej… |
| CargaBDeposito.frm | 2615 | SELECT | rs_nroasiento.Open "select * from cont_ejercicio where activ… |
| PNotaCred.frm | 6948 | SELECT | rs_ejercicio.Open "Select * from cont_ejercicio where id_eje… |
| PNotaCred.frm | 6950 | SELECT | rs_ejercicio.Open "Select * from cont_ejercicio where activo… |
| PNotaCred.frm | 6998 | SELECT | rs_nroasiento.Open "select * from cont_ejercicio where id_ej… |
| PNotaCred.frm | 7000 | SELECT | rs_nroasiento.Open "select * from cont_ejercicio where activ… |
| Visualiza_ReciboCobro.frm | 15406 | SELECT | rs_ejercicio.Open "Select * from cont_ejercicio where activo… |
| Visualiza_ReciboCobro.frm | 15439 | SELECT | rs_nroasiento.Open "select * from cont_ejercicio where activ… |
| Visualiza_NotaCred.frm | 5565 | SELECT | rs_ejercicio.Open "Select * from cont_ejercicio where activo… |
| Visualiza_NotaCred.frm | 5598 | SELECT | rs_nroasiento.Open "select * from cont_ejercicio where activ… |
| Cont_CargaPlanCta.frm | 751 | SELECT | rs_ejercicio.Open "Select DISTINCT id_ejercicio from cont_ej… |
| Visualiza_CargaMovStock.frm | 5346 | SELECT | rs_ejercicio.Open "Select * from cont_ejercicio where activo… |
| Visualiza_CargaMovStock.frm | 5379 | SELECT | rs_nroasiento.Open "select * from cont_ejercicio where activ… |
| NotaCredCon.frm | 7290 | SELECT | rs_ejercicio.Open "Select * from cont_ejercicio where id_eje… |
| NotaCredCon.frm | 7292 | SELECT | rs_ejercicio.Open "Select * from cont_ejercicio where activo… |
| NotaCredCon.frm | 7340 | SELECT | rs_nroasiento.Open "select * from cont_ejercicio where id_ej… |
| NotaCredCon.frm | 7342 | SELECT | rs_nroasiento.Open "select * from cont_ejercicio where activ… |
| Visualiza_PNotaDeb.frm | 3825 | SELECT | rs_ejercicio.Open "Select * from cont_ejercicio where activo… |
| Visualiza_PNotaDeb.frm | 3858 | SELECT | rs_nroasiento.Open "select * from cont_ejercicio where activ… |
| FacturaB_COPIA.frm | 12039 | SELECT | rs_ejercicio.Open "Select * from cont_ejercicio where id_eje… |
| FacturaB_COPIA.frm | 12041 | SELECT | rs_ejercicio.Open "Select * from cont_ejercicio where activo… |
| FacturaB_COPIA.frm | 12089 | SELECT | rs_nroasiento.Open "select * from cont_ejercicio where id_ej… |
| FacturaB_COPIA.frm | 12091 | SELECT | rs_nroasiento.Open "select * from cont_ejercicio where activ… |
| FacturaB_COPIA.frm | 16240 | SELECT | rs_nroasiento.Open "select * from cont_ejercicio where id_ej… |
| FacturaB_COPIA.frm | 16242 | SELECT | rs_nroasiento.Open "select * from cont_ejercicio where activ… |
| NotaCredDesc.frm | 4373 | SELECT | rs_ejercicio.Open "Select * from cont_ejercicio where id_eje… |
| NotaCredDesc.frm | 4375 | SELECT | rs_ejercicio.Open "Select * from cont_ejercicio where activo… |
| NotaCredDesc.frm | 4423 | SELECT | rs_nroasiento.Open "select * from cont_ejercicio where id_ej… |
| NotaCredDesc.frm | 4425 | SELECT | rs_nroasiento.Open "select * from cont_ejercicio where activ… |
| NotaCred_COPIA.frm | 8773 | SELECT | rs_ejercicio.Open "Select * from cont_ejercicio where id_eje… |
| NotaCred_COPIA.frm | 8775 | SELECT | rs_ejercicio.Open "Select * from cont_ejercicio where activo… |
| NotaCred_COPIA.frm | 8823 | SELECT | rs_nroasiento.Open "select * from cont_ejercicio where id_ej… |
| NotaCred_COPIA.frm | 8825 | SELECT | rs_nroasiento.Open "select * from cont_ejercicio where activ… |
| NotaCred_COPIA.frm | 11836 | SELECT | rs_nroasiento.Open "select * from cont_ejercicio where id_ej… |
| NotaCred_COPIA.frm | 11838 | SELECT | rs_nroasiento.Open "select * from cont_ejercicio where activ… |
| Visualiza_TPV.frm | 9184 | SELECT | rs_ejercicio.Open "Select * from cont_ejercicio where activo… |
| Visualiza_TPV.frm | 9217 | SELECT | rs_nroasiento.Open "select * from cont_ejercicio where activ… |
| Visualiza_TPV.frm | 10239 | SELECT | rs_ejercicio.Open "Select * from cont_ejercicio where activo… |
| Visualiza_TPV.frm | 10272 | SELECT | rs_nroasiento.Open "select * from cont_ejercicio where activ… |
| ChequeTercero.frm | 2797 | SELECT | rs_nroasiento.Open "select * from cont_ejercicio where activ… |
| ChequeTercero.frm | 2862 | SELECT | rs_ejercicio.Open "Select * from cont_ejercicio where activo… |
| TPV.frm | 19277 | SELECT | rs_ejercicio.Open "Select * from cont_ejercicio where activo… |
| TPV.frm | 19319 | SELECT | rs_nroasiento.Open "select * from cont_ejercicio where activ… |
| TPV.frm | 20600 | SELECT | rs_ejercicio.Open "Select * from cont_ejercicio where activo… |
| TPV.frm | 20642 | SELECT | rs_nroasiento.Open "select * from cont_ejercicio where activ… |
| TPV.frm | 24985 | SELECT | rs_nroasiento.Open "select * from cont_ejercicio where id_ej… |
| TPV.frm | 24987 | SELECT | rs_nroasiento.Open "select * from cont_ejercicio where activ… |
| TPV.frm | 25683 | SELECT | rs_nroasiento.Open "select * from cont_ejercicio where id_ej… |
| TPV.frm | 25685 | SELECT | rs_nroasiento.Open "select * from cont_ejercicio where activ… |
| Cont_ProcAsientosM.frm | 1004 | SELECT | rs_ejercicio.Open "Select * from cont_ejercicio where activo… |
| Cont_ProcAsientosM.frm | 1293 | SELECT | rs_ejercicio.Open "Select * from cont_ejercicio where activo… |
| Cont_ProcAsientosM.frm | 1846 | SELECT | rs_cerrado.Open "SELECT cerrado from cont_ejercicio WHERE id… |
| Cont_ProcAsientosM.frm | 1907 | SELECT | rs_nroasiento.Open "select * from cont_ejercicio where activ… |
| Cont_ProcAsientosM.frm | 1910 | SELECT | '        rs_nroasiento.Open "select * from cont_ejercicio wh… |
| Cont_ProcAsientosM.frm | 1973 | SELECT | rs_ejercicio.Open "Select * from cont_ejercicio where activo… |
| Visualiza_NotaCredDesc.frm | 2170 | SELECT | rs_ejercicio.Open "Select * from cont_ejercicio where activo… |
| Visualiza_NotaCredDesc.frm | 2203 | SELECT | rs_nroasiento.Open "select * from cont_ejercicio where activ… |
| CuentaCliente.frm | 3501 | SELECT | rs_nroasiento.Open "select * from cont_ejercicio where activ… |
| CuentaCliente.frm | 3566 | SELECT | rs_ejercicio.Open "Select * from cont_ejercicio where activo… |
| CargaMovCaja.frm | 4419 | SELECT | rs_ejercicio.Open "Select * from cont_ejercicio where id_eje… |
| CargaMovCaja.frm | 4421 | SELECT | rs_ejercicio.Open "Select * from cont_ejercicio where activo… |
| CargaMovCaja.frm | 4469 | SELECT | rs_nroasiento.Open "select * from cont_ejercicio where id_ej… |
| CargaMovCaja.frm | 4471 | SELECT | rs_nroasiento.Open "select * from cont_ejercicio where activ… |
| OrdenPago.frm | 14607 | SELECT | rs_ejercicio.Open "Select * from cont_ejercicio where id_eje… |
| OrdenPago.frm | 14609 | SELECT | rs_ejercicio.Open "Select * from cont_ejercicio where activo… |
| OrdenPago.frm | 14657 | SELECT | rs_nroasiento.Open "select * from cont_ejercicio where id_ej… |
| OrdenPago.frm | 14659 | SELECT | rs_nroasiento.Open "select * from cont_ejercicio where activ… |
| Imp_Carga.frm | 442 | SELECT | rs_ejercicio.Open "SELECT * FROM cont_ejercicio WHERE id_eje… |
| Imp_Carga.frm | 446 | SELECT | rs_ejercicio.Open "Select * from cont_ejercicio where activo… |
| Imp_Carga.frm | 1055 | SELECT | rs_ejercicio.Open "Select * from cont_ejercicio where activo… |
| Imp_Carga.frm | 1097 | SELECT | rs_nroasiento.Open "select * from cont_ejercicio where activ… |
| Visualiza_PNotaCred_Importe.frm | 3739 | SELECT | rs_ejercicio.Open "Select * from cont_ejercicio where activo… |
| Visualiza_PNotaCred_Importe.frm | 3772 | SELECT | rs_nroasiento.Open "select * from cont_ejercicio where activ… |
| Visualiza_FB_Copia.frm | 7250 | SELECT | rs_ejercicio.Open "Select * from cont_ejercicio where activo… |
| Visualiza_FB_Copia.frm | 7283 | SELECT | rs_nroasiento.Open "select * from cont_ejercicio where activ… |
| Visualiza_PNotaCredDev.frm | 5704 | SELECT | rs_ejercicio.Open "Select * from cont_ejercicio where activo… |
| Visualiza_PNotaCredDev.frm | 5737 | SELECT | rs_nroasiento.Open "select * from cont_ejercicio where activ… |
| Visualiza_PNotaCredDesc.frm | 2857 | SELECT | rs_ejercicio.Open "Select * from cont_ejercicio where activo… |
| … | … | … | *(256 referencias más)* |

---

## 4. Uso en Synap (reports)

| Archivo | Línea | Operación | Fragmento |
|---------|-------|-----------|-----------|
| services/reconciliation_saldo_pedido_proveedor.py | 66 | SELECT | FROM cont_ejercicio |
| services/reconciliation_saldo_pedido_proveedor.py | 98 | SELECT | FROM cont_ejercicio WHERE id_ejercicio = %s |
| services/reconciliation_saldo_pedido_proveedor.py | 107 | SELECT | FROM cont_ejercicio |

[← Índice de tablas](../DB_INDICE_TABLAS.md)