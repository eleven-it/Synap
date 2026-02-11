# Tabla `cont_periodo_saldo_cta`

Base: **administranet**

---

## 1. Schema (information_schema)

### 1.1 Columnas

| Campo | Tipo | Nulo | PK | FK | Referencia |
|-------|------|------|----|----|------------|
| id_cont_periodo_saldo_cta | DOUBLE | No | ✓ |  |  |
| id_pc | DOUBLE | Sí |  |  |  |
| id_ejercicio | DOUBLE | Sí |  |  |  |
| id_periodo | DOUBLE | Sí |  |  |  |
| saldo_periodo_cta | DECIMAL | Sí |  |  |  |

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
| CargaBDeposito.frm | 2711 | SELECT | rs_SaldoCtaCont.Open "SELECT * FROM cont_periodo_saldo_cta w… |
| PNotaCred.frm | 7095 | SELECT | rs_SaldoCtaCont.Open "SELECT * FROM cont_periodo_saldo_cta w… |
| Visualiza_ReciboCobro.frm | 15533 | SELECT | rs_SaldoCtaCont.Open "SELECT * FROM cont_periodo_saldo_cta w… |
| Visualiza_NotaCred.frm | 5692 | SELECT | rs_SaldoCtaCont.Open "SELECT * FROM cont_periodo_saldo_cta w… |
| Cont_CargaPlanCta.frm | 782 | SELECT | rs_ctamayor.Open "SELECT * from cont_periodo_saldo_cta where… |
| Visualiza_CargaMovStock.frm | 5473 | SELECT | rs_SaldoCtaCont.Open "SELECT * FROM cont_periodo_saldo_cta w… |
| NotaCredCon.frm | 7437 | SELECT | rs_SaldoCtaCont.Open "SELECT * FROM cont_periodo_saldo_cta w… |
| Visualiza_PNotaDeb.frm | 3952 | SELECT | rs_SaldoCtaCont.Open "SELECT * FROM cont_periodo_saldo_cta w… |
| FacturaB_COPIA.frm | 12186 | SELECT | rs_SaldoCtaCont.Open "SELECT * FROM cont_periodo_saldo_cta w… |
| FacturaB_COPIA.frm | 12215 | UPDATE | '                    conn.Execute "UPDATE cont_periodo_saldo… |
| FacturaB_COPIA.frm | 16345 | SELECT | rs_SaldoCtaCont.Open "SELECT * FROM cont_periodo_saldo_cta w… |
| NotaCredDesc.frm | 4520 | SELECT | rs_SaldoCtaCont.Open "SELECT * FROM cont_periodo_saldo_cta w… |
| NotaCred_COPIA.frm | 8920 | SELECT | rs_SaldoCtaCont.Open "SELECT * FROM cont_periodo_saldo_cta w… |
| NotaCred_COPIA.frm | 11941 | SELECT | rs_SaldoCtaCont.Open "SELECT * FROM cont_periodo_saldo_cta w… |
| Visualiza_TPV.frm | 9311 | SELECT | rs_SaldoCtaCont.Open "SELECT * FROM cont_periodo_saldo_cta w… |
| Visualiza_TPV.frm | 10366 | SELECT | rs_SaldoCtaCont.Open "SELECT * FROM cont_periodo_saldo_cta w… |
| ChequeTercero.frm | 3004 | SELECT | rs_SaldoCtaCont.Open "SELECT * FROM cont_periodo_saldo_cta w… |
| Cont_CargaPerido.frm | 514 | SELECT | rs_EjerCtas.Open "Select * from cont_periodo_saldo_cta", con… |
| TPV.frm | 19413 | SELECT | rs_SaldoCtaCont.Open "SELECT * FROM cont_periodo_saldo_cta w… |
| TPV.frm | 20736 | SELECT | rs_SaldoCtaCont.Open "SELECT * FROM cont_periodo_saldo_cta w… |
| TPV.frm | 25090 | SELECT | rs_SaldoCtaCont.Open "SELECT * FROM cont_periodo_saldo_cta w… |
| TPV.frm | 25788 | SELECT | rs_SaldoCtaCont.Open "SELECT * FROM cont_periodo_saldo_cta w… |
| Cont_ProcAsientosM.frm | 2134 | SELECT | rs_SaldoCtaCont.Open "SELECT * FROM cont_periodo_saldo_cta w… |
| Visualiza_NotaCredDesc.frm | 2297 | SELECT | rs_SaldoCtaCont.Open "SELECT * FROM cont_periodo_saldo_cta w… |
| CuentaCliente.frm | 3708 | SELECT | rs_SaldoCtaCont.Open "SELECT * FROM cont_periodo_saldo_cta w… |
| CargaMovCaja.frm | 4567 | SELECT | rs_SaldoCtaCont.Open "SELECT * FROM cont_periodo_saldo_cta w… |
| OrdenPago.frm | 14754 | SELECT | rs_SaldoCtaCont.Open "SELECT * FROM cont_periodo_saldo_cta w… |
| Imp_Carga.frm | 1191 | SELECT | rs_SaldoCtaCont.Open "SELECT * FROM cont_periodo_saldo_cta w… |
| Visualiza_PNotaCred_Importe.frm | 3866 | SELECT | rs_SaldoCtaCont.Open "SELECT * FROM cont_periodo_saldo_cta w… |
| Visualiza_FB_Copia.frm | 7377 | SELECT | rs_SaldoCtaCont.Open "SELECT * FROM cont_periodo_saldo_cta w… |
| Visualiza_PNotaCredDev.frm | 5831 | SELECT | rs_SaldoCtaCont.Open "SELECT * FROM cont_periodo_saldo_cta w… |
| Visualiza_PNotaCredDesc.frm | 2984 | SELECT | rs_SaldoCtaCont.Open "SELECT * FROM cont_periodo_saldo_cta w… |
| FacturaB.frm | 18025 | SELECT | rs_SaldoCtaCont.Open "SELECT * FROM cont_periodo_saldo_cta w… |
| FacturaB.frm | 18054 | UPDATE | '                    conn.Execute "UPDATE cont_periodo_saldo… |
| FacturaB.frm | 22405 | SELECT | rs_SaldoCtaCont.Open "SELECT * FROM cont_periodo_saldo_cta w… |
| CargaExtraccion.frm | 1334 | SELECT | rs_SaldoCtaCont.Open "SELECT * FROM cont_periodo_saldo_cta w… |
| NotaCred_SinCompO.frm | 11285 | SELECT | rs_SaldoCtaCont.Open "SELECT * FROM cont_periodo_saldo_cta w… |
| NotaCred_SinCompO.frm | 14235 | SELECT | rs_SaldoCtaCont.Open "SELECT * FROM cont_periodo_saldo_cta w… |
| FacturaA.frm | 14080 | SELECT | rs_SaldoCtaCont.Open "SELECT * FROM cont_periodo_saldo_cta w… |
| FacturaA.frm | 19015 | SELECT | rs_SaldoCtaCont.Open "SELECT * FROM cont_periodo_saldo_cta w… |
| Cont_ListaCtaCont.frm | 719 | JOIN | "LEFT JOIN cont_periodo_saldo_cta on (cont_periodo_saldo_cta… |
| Cont_ListaCtaCont.frm | 803 | JOIN | "LEFT JOIN cont_periodo_saldo_cta on (cont_periodo_saldo_cta… |
| Cont_ListaCtaCont.frm | 1531 | JOIN | "LEFT JOIN cont_periodo_saldo_cta on (cont_periodo_saldo_cta… |
| Visualiza_NotaDeb.frm | 4276 | SELECT | rs_SaldoCtaCont.Open "SELECT * FROM cont_periodo_saldo_cta w… |
| PNotaDebCopia.frm | 4431 | SELECT | rs_SaldoCtaCont.Open "SELECT * FROM cont_periodo_saldo_cta w… |
| NotaCred_Importe.frm | 6846 | SELECT | rs_SaldoCtaCont.Open "SELECT * FROM cont_periodo_saldo_cta w… |
| NotaCred_Importe.frm | 9773 | SELECT | rs_SaldoCtaCont.Open "SELECT * FROM cont_periodo_saldo_cta w… |
| CargaGastoBancario.frm | 2098 | SELECT | rs_SaldoCtaCont.Open "SELECT * FROM cont_periodo_saldo_cta w… |
| Visualiza_Cont_CargaAsientoM.frm | 1347 | SELECT | rs_SaldoCtaCont.Open "SELECT * FROM cont_periodo_saldo_cta w… |
| Visualiza_Cont_CargaAsientoM.frm | 1684 | SELECT | rs_SaldoCtaCont.Open "SELECT * FROM cont_periodo_saldo_cta w… |
| Visualiza_Cont_CargaAsientoM.frm | 1824 | SELECT | rs_SaldoCtaCont.Open "SELECT * FROM cont_periodo_saldo_cta w… |
| Visualiza_FA.frm | 7217 | SELECT | rs_SaldoCtaCont.Open "SELECT * FROM cont_periodo_saldo_cta w… |
| Inventario.frm | 2660 | SELECT | rs_SaldoCtaCont.Open "SELECT * FROM cont_periodo_saldo_cta w… |
| Inventario.frm | 3334 | SELECT | rs_SaldoCtaCont.Open "SELECT * FROM cont_periodo_saldo_cta w… |
| NotaCredCopia.frm | 9799 | SELECT | rs_SaldoCtaCont.Open "SELECT * FROM cont_periodo_saldo_cta w… |
| NotaCredCopia.frm | 13109 | SELECT | rs_SaldoCtaCont.Open "SELECT * FROM cont_periodo_saldo_cta w… |
| Visualiza_NotaCred_Importe.frm | 3355 | SELECT | rs_SaldoCtaCont.Open "SELECT * FROM cont_periodo_saldo_cta w… |
| Cont_CargaAsientoM.frm | 1610 | SELECT | rs_SaldoCtaCont.Open "SELECT * FROM cont_periodo_saldo_cta w… |
| Cont_CargaAsientoM.frm | 1736 | SELECT | rs_SaldoCtaCont.Open "SELECT * FROM cont_periodo_saldo_cta w… |
| Cont_CargaAsientoM.frm | 2187 | SELECT | rs_SaldoCtaCont.Open "SELECT * FROM cont_periodo_saldo_cta w… |
| Cont_CargaAsientoM.frm | 2326 | SELECT | rs_SaldoCtaCont.Open "SELECT * FROM cont_periodo_saldo_cta w… |
| Visualiza_PNotaCred_ImporteCopia.frm | 3736 | SELECT | rs_SaldoCtaCont.Open "SELECT * FROM cont_periodo_saldo_cta w… |
| Visualiza_FB.frm | 7912 | SELECT | rs_SaldoCtaCont.Open "SELECT * FROM cont_periodo_saldo_cta w… |
| PFactura.frm | 9736 | SELECT | rs_SaldoCtaCont.Open "SELECT * FROM cont_periodo_saldo_cta w… |
| ConsultaComprobante.frm | 28027 | SELECT | rs_SaldoCtaCont.Open "SELECT * FROM cont_periodo_saldo_cta w… |
| ConsultaComprobante.frm | 28032 | SELECT | rs_SaldoCtaCont.Open "SELECT * FROM cont_periodo_saldo_cta w… |
| ConsultaComprobante.frm | 28434 | SELECT | rs_SaldoCtaCont.Open "SELECT * FROM cont_periodo_saldo_cta w… |
| ConsultaComprobante.frm | 28856 | SELECT | rs_SaldoCtaCont.Open "SELECT * FROM cont_periodo_saldo_cta w… |
| ConsultaComprobante.frm | 29327 | SELECT | rs_SaldoCtaCont.Open "SELECT * FROM cont_periodo_saldo_cta w… |
| CargaLiquidacionTC.frm | 2980 | SELECT | rs_SaldoCtaCont.Open "SELECT * FROM cont_periodo_saldo_cta w… |
| NotaDeb.frm | 8348 | SELECT | rs_SaldoCtaCont.Open "SELECT * FROM cont_periodo_saldo_cta w… |
| NotaDeb.frm | 11218 | SELECT | rs_SaldoCtaCont.Open "SELECT * FROM cont_periodo_saldo_cta w… |
| NotaDeb.frm | 11991 | SELECT | rs_SaldoCtaCont.Open "SELECT * FROM cont_periodo_saldo_cta w… |
| PNotaCredDesc.frm | 2907 | SELECT | rs_SaldoCtaCont.Open "SELECT * FROM cont_periodo_saldo_cta w… |
| CargaClearing.frm | 1464 | SELECT | rs_SaldoCtaCont.Open "SELECT * FROM cont_periodo_saldo_cta w… |
| Visualiza_PFactura_Copia.frm | 7305 | SELECT | rs_SaldoCtaCont.Open "SELECT * FROM cont_periodo_saldo_cta w… |
| PNotaCred_Importe.frm | 4200 | SELECT | rs_SaldoCtaCont.Open "SELECT * FROM cont_periodo_saldo_cta w… |
| CargaTransBancaria.frm | 1532 | SELECT | rs_SaldoCtaCont.Open "SELECT * FROM cont_periodo_saldo_cta w… |
| Cont_ProcesosC.frm | 691 | JOIN | "RIGHT JOIN cont_periodo_saldo_cta ON (cont_periodo_saldo_ct… |
| Cont_ProcesosC.frm | 775 | JOIN | "RIGHT JOIN cont_periodo_saldo_cta ON (cont_periodo_saldo_ct… |
| … | … | … | *(44 referencias más)* |

---

## 4. Uso en Synap (reports)

*No se encontraron referencias en el módulo reports.*

[← Índice de tablas](../DB_INDICE_TABLAS.md)