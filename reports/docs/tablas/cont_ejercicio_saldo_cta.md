# Tabla `cont_ejercicio_saldo_cta`

Base: **administranet**

---

## 1. Schema (information_schema)

### 1.1 Columnas

| Campo | Tipo | Nulo | PK | FK | Referencia |
|-------|------|------|----|----|------------|
| id_cont_ejercicio_saldo_cta | DOUBLE | No | ✓ |  |  |
| id_pc | DOUBLE | Sí |  |  |  |
| id_ejercicio | DOUBLE | Sí |  |  |  |
| saldo_ejercicio_cta | DECIMAL | Sí |  |  |  |

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
| CargaBDeposito.frm | 2672 | SELECT | rs_SaldoCtaCont.Open "SELECT * FROM cont_ejercicio_saldo_cta… |
| CargaBDeposito.frm | 2751 | SELECT | rs_SaldoCtaCont.Open "SELECT * FROM cont_ejercicio_saldo_cta… |
| PNotaCred.frm | 7057 | SELECT | rs_SaldoCtaCont.Open "SELECT * FROM cont_ejercicio_saldo_cta… |
| PNotaCred.frm | 7135 | SELECT | rs_SaldoCtaCont.Open "SELECT * FROM cont_ejercicio_saldo_cta… |
| Visualiza_ReciboCobro.frm | 15495 | SELECT | rs_SaldoCtaCont.Open "SELECT * FROM cont_ejercicio_saldo_cta… |
| Visualiza_ReciboCobro.frm | 15573 | SELECT | rs_SaldoCtaCont.Open "SELECT * FROM cont_ejercicio_saldo_cta… |
| Visualiza_NotaCred.frm | 5654 | SELECT | rs_SaldoCtaCont.Open "SELECT * FROM cont_ejercicio_saldo_cta… |
| Visualiza_NotaCred.frm | 5732 | SELECT | rs_SaldoCtaCont.Open "SELECT * FROM cont_ejercicio_saldo_cta… |
| Cont_CargaPlanCta.frm | 756 | SELECT | rs_ctamayor.Open "SELECT * from cont_ejercicio_saldo_cta whe… |
| Visualiza_CargaMovStock.frm | 5435 | SELECT | rs_SaldoCtaCont.Open "SELECT * FROM cont_ejercicio_saldo_cta… |
| Visualiza_CargaMovStock.frm | 5513 | SELECT | rs_SaldoCtaCont.Open "SELECT * FROM cont_ejercicio_saldo_cta… |
| NotaCredCon.frm | 7399 | SELECT | rs_SaldoCtaCont.Open "SELECT * FROM cont_ejercicio_saldo_cta… |
| NotaCredCon.frm | 7477 | SELECT | rs_SaldoCtaCont.Open "SELECT * FROM cont_ejercicio_saldo_cta… |
| Visualiza_PNotaDeb.frm | 3914 | SELECT | rs_SaldoCtaCont.Open "SELECT * FROM cont_ejercicio_saldo_cta… |
| Visualiza_PNotaDeb.frm | 3992 | SELECT | rs_SaldoCtaCont.Open "SELECT * FROM cont_ejercicio_saldo_cta… |
| FacturaB_COPIA.frm | 12148 | SELECT | rs_SaldoCtaCont.Open "SELECT * FROM cont_ejercicio_saldo_cta… |
| FacturaB_COPIA.frm | 12234 | SELECT | rs_SaldoCtaCont.Open "SELECT * FROM cont_ejercicio_saldo_cta… |
| FacturaB_COPIA.frm | 16307 | SELECT | rs_SaldoCtaCont.Open "SELECT * FROM cont_ejercicio_saldo_cta… |
| FacturaB_COPIA.frm | 16385 | SELECT | rs_SaldoCtaCont.Open "SELECT * FROM cont_ejercicio_saldo_cta… |
| NotaCredDesc.frm | 4482 | SELECT | rs_SaldoCtaCont.Open "SELECT * FROM cont_ejercicio_saldo_cta… |
| NotaCredDesc.frm | 4560 | SELECT | rs_SaldoCtaCont.Open "SELECT * FROM cont_ejercicio_saldo_cta… |
| NotaCred_COPIA.frm | 8882 | SELECT | rs_SaldoCtaCont.Open "SELECT * FROM cont_ejercicio_saldo_cta… |
| NotaCred_COPIA.frm | 8960 | SELECT | rs_SaldoCtaCont.Open "SELECT * FROM cont_ejercicio_saldo_cta… |
| NotaCred_COPIA.frm | 11903 | SELECT | rs_SaldoCtaCont.Open "SELECT * FROM cont_ejercicio_saldo_cta… |
| NotaCred_COPIA.frm | 11981 | SELECT | rs_SaldoCtaCont.Open "SELECT * FROM cont_ejercicio_saldo_cta… |
| Visualiza_TPV.frm | 9273 | SELECT | rs_SaldoCtaCont.Open "SELECT * FROM cont_ejercicio_saldo_cta… |
| Visualiza_TPV.frm | 9351 | SELECT | rs_SaldoCtaCont.Open "SELECT * FROM cont_ejercicio_saldo_cta… |
| Visualiza_TPV.frm | 10328 | SELECT | rs_SaldoCtaCont.Open "SELECT * FROM cont_ejercicio_saldo_cta… |
| Visualiza_TPV.frm | 10406 | SELECT | rs_SaldoCtaCont.Open "SELECT * FROM cont_ejercicio_saldo_cta… |
| ChequeTercero.frm | 2976 | SELECT | rs_SaldoCtaCont.Open "SELECT * FROM cont_ejercicio_saldo_cta… |
| ChequeTercero.frm | 3038 | SELECT | rs_SaldoCtaCont.Open "SELECT * FROM cont_ejercicio_saldo_cta… |
| TPV.frm | 19375 | SELECT | rs_SaldoCtaCont.Open "SELECT * FROM cont_ejercicio_saldo_cta… |
| TPV.frm | 19453 | SELECT | rs_SaldoCtaCont.Open "SELECT * FROM cont_ejercicio_saldo_cta… |
| TPV.frm | 20698 | SELECT | rs_SaldoCtaCont.Open "SELECT * FROM cont_ejercicio_saldo_cta… |
| TPV.frm | 20776 | SELECT | rs_SaldoCtaCont.Open "SELECT * FROM cont_ejercicio_saldo_cta… |
| TPV.frm | 25052 | SELECT | rs_SaldoCtaCont.Open "SELECT * FROM cont_ejercicio_saldo_cta… |
| TPV.frm | 25130 | SELECT | rs_SaldoCtaCont.Open "SELECT * FROM cont_ejercicio_saldo_cta… |
| TPV.frm | 25750 | SELECT | rs_SaldoCtaCont.Open "SELECT * FROM cont_ejercicio_saldo_cta… |
| TPV.frm | 25828 | SELECT | rs_SaldoCtaCont.Open "SELECT * FROM cont_ejercicio_saldo_cta… |
| Cont_ProcAsientosM.frm | 2106 | SELECT | rs_SaldoCtaCont.Open "SELECT * FROM cont_ejercicio_saldo_cta… |
| Cont_ProcAsientosM.frm | 2168 | SELECT | rs_SaldoCtaCont.Open "SELECT * FROM cont_ejercicio_saldo_cta… |
| Visualiza_NotaCredDesc.frm | 2259 | SELECT | rs_SaldoCtaCont.Open "SELECT * FROM cont_ejercicio_saldo_cta… |
| Visualiza_NotaCredDesc.frm | 2337 | SELECT | rs_SaldoCtaCont.Open "SELECT * FROM cont_ejercicio_saldo_cta… |
| CuentaCliente.frm | 3680 | SELECT | rs_SaldoCtaCont.Open "SELECT * FROM cont_ejercicio_saldo_cta… |
| CuentaCliente.frm | 3742 | SELECT | rs_SaldoCtaCont.Open "SELECT * FROM cont_ejercicio_saldo_cta… |
| CargaMovCaja.frm | 4528 | SELECT | rs_SaldoCtaCont.Open "SELECT * FROM cont_ejercicio_saldo_cta… |
| CargaMovCaja.frm | 4607 | SELECT | rs_SaldoCtaCont.Open "SELECT * FROM cont_ejercicio_saldo_cta… |
| OrdenPago.frm | 14716 | SELECT | rs_SaldoCtaCont.Open "SELECT * FROM cont_ejercicio_saldo_cta… |
| OrdenPago.frm | 14799 | SELECT | rs_SaldoCtaCont.Open "SELECT * FROM cont_ejercicio_saldo_cta… |
| Imp_Carga.frm | 1153 | SELECT | rs_SaldoCtaCont.Open "SELECT * FROM cont_ejercicio_saldo_cta… |
| Imp_Carga.frm | 1231 | SELECT | rs_SaldoCtaCont.Open "SELECT * FROM cont_ejercicio_saldo_cta… |
| Visualiza_PNotaCred_Importe.frm | 3828 | SELECT | rs_SaldoCtaCont.Open "SELECT * FROM cont_ejercicio_saldo_cta… |
| Visualiza_PNotaCred_Importe.frm | 3906 | SELECT | rs_SaldoCtaCont.Open "SELECT * FROM cont_ejercicio_saldo_cta… |
| Visualiza_FB_Copia.frm | 7339 | SELECT | rs_SaldoCtaCont.Open "SELECT * FROM cont_ejercicio_saldo_cta… |
| Visualiza_FB_Copia.frm | 7417 | SELECT | rs_SaldoCtaCont.Open "SELECT * FROM cont_ejercicio_saldo_cta… |
| Visualiza_PNotaCredDev.frm | 5793 | SELECT | rs_SaldoCtaCont.Open "SELECT * FROM cont_ejercicio_saldo_cta… |
| Visualiza_PNotaCredDev.frm | 5871 | SELECT | rs_SaldoCtaCont.Open "SELECT * FROM cont_ejercicio_saldo_cta… |
| Visualiza_PNotaCredDesc.frm | 2946 | SELECT | rs_SaldoCtaCont.Open "SELECT * FROM cont_ejercicio_saldo_cta… |
| Visualiza_PNotaCredDesc.frm | 3024 | SELECT | rs_SaldoCtaCont.Open "SELECT * FROM cont_ejercicio_saldo_cta… |
| FacturaB.frm | 17987 | SELECT | rs_SaldoCtaCont.Open "SELECT * FROM cont_ejercicio_saldo_cta… |
| FacturaB.frm | 18073 | SELECT | rs_SaldoCtaCont.Open "SELECT * FROM cont_ejercicio_saldo_cta… |
| FacturaB.frm | 22366 | SELECT | rs_SaldoCtaCont.Open "SELECT * FROM cont_ejercicio_saldo_cta… |
| FacturaB.frm | 22446 | SELECT | rs_SaldoCtaCont.Open "SELECT * FROM cont_ejercicio_saldo_cta… |
| CargaExtraccion.frm | 1295 | SELECT | rs_SaldoCtaCont.Open "SELECT * FROM cont_ejercicio_saldo_cta… |
| CargaExtraccion.frm | 1374 | SELECT | rs_SaldoCtaCont.Open "SELECT * FROM cont_ejercicio_saldo_cta… |
| NotaCred_SinCompO.frm | 11247 | SELECT | rs_SaldoCtaCont.Open "SELECT * FROM cont_ejercicio_saldo_cta… |
| NotaCred_SinCompO.frm | 11325 | SELECT | rs_SaldoCtaCont.Open "SELECT * FROM cont_ejercicio_saldo_cta… |
| NotaCred_SinCompO.frm | 14197 | SELECT | rs_SaldoCtaCont.Open "SELECT * FROM cont_ejercicio_saldo_cta… |
| NotaCred_SinCompO.frm | 14275 | SELECT | rs_SaldoCtaCont.Open "SELECT * FROM cont_ejercicio_saldo_cta… |
| FacturaA.frm | 14042 | SELECT | rs_SaldoCtaCont.Open "SELECT * FROM cont_ejercicio_saldo_cta… |
| FacturaA.frm | 14121 | SELECT | rs_SaldoCtaCont.Open "SELECT * FROM cont_ejercicio_saldo_cta… |
| FacturaA.frm | 18977 | SELECT | rs_SaldoCtaCont.Open "SELECT * FROM cont_ejercicio_saldo_cta… |
| FacturaA.frm | 19056 | SELECT | rs_SaldoCtaCont.Open "SELECT * FROM cont_ejercicio_saldo_cta… |
| Cont_ListaCtaCont.frm | 730 | JOIN | "LEFT JOIN cont_ejercicio_saldo_cta on (cont_ejercicio_saldo… |
| Cont_ListaCtaCont.frm | 814 | JOIN | "LEFT JOIN cont_ejercicio_saldo_cta on (cont_ejercicio_saldo… |
| Cont_ListaCtaCont.frm | 1546 | JOIN | "LEFT JOIN cont_ejercicio_saldo_cta on (cont_ejercicio_saldo… |
| Visualiza_NotaDeb.frm | 4238 | SELECT | rs_SaldoCtaCont.Open "SELECT * FROM cont_ejercicio_saldo_cta… |
| Visualiza_NotaDeb.frm | 4316 | SELECT | rs_SaldoCtaCont.Open "SELECT * FROM cont_ejercicio_saldo_cta… |
| PNotaDebCopia.frm | 4393 | SELECT | rs_SaldoCtaCont.Open "SELECT * FROM cont_ejercicio_saldo_cta… |
| PNotaDebCopia.frm | 4471 | SELECT | rs_SaldoCtaCont.Open "SELECT * FROM cont_ejercicio_saldo_cta… |
| … | … | … | *(154 referencias más)* |

---

## 4. Uso en Synap (reports)

*No se encontraron referencias en el módulo reports.*

[← Índice de tablas](../DB_INDICE_TABLAS.md)