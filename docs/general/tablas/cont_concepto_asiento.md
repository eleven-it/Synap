# Tabla `cont_concepto_asiento`

Base: **administranet**

---

## 1. Schema (information_schema)

### 1.1 Columnas

| Campo | Tipo | Nulo | PK | FK | Referencia |
|-------|------|------|----|----|------------|
| id_concepto_asiento | DOUBLE | No | ✓ |  |  |
| desc_concepto_asiento | VARCHAR | Sí |  |  |  |
| tipo_concepto_asiento | VARCHAR | Sí |  |  |  |
| id_concepto_anul | INT | Sí |  |  |  |
| anulado | VARCHAR | Sí |  |  |  |
| tipo_concepto | VARCHAR | Sí |  |  |  |

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
| CargaBDeposito.frm | 2854 | SELECT | rs_concepto.Open "SELECt desc_concepto_asiento from cont_con… |
| PNotaCred.frm | 7250 | SELECT | rs_concepto.Open "SELECt desc_concepto_asiento from cont_con… |
| Visualiza_ReciboCobro.frm | 15679 | SELECT | rs_concepto.Open "SELECt desc_concepto_asiento from cont_con… |
| Cont_Conceptos_Cont.frm | 443 | SELECT | Data_Concepto_Asiento.RecordSource = "select * from cont_con… |
| Cont_Conceptos_Cont.frm | 483 | SELECT | Data_Concepto_Asiento.RecordSource = "select * from cont_con… |
| Visualiza_NotaCred.frm | 5836 | SELECT | rs_concepto.Open "SELECt desc_concepto_asiento from cont_con… |
| Visualiza_CargaMovStock.frm | 5616 | SELECT | rs_concepto.Open "SELECt desc_concepto_asiento from cont_con… |
| NotaCredCon.frm | 7581 | SELECT | rs_concepto.Open "SELECT desc_concepto_asiento from cont_con… |
| Visualiza_PNotaDeb.frm | 4098 | SELECT | rs_concepto.Open "SELECt desc_concepto_asiento from cont_con… |
| FacturaB_COPIA.frm | 12337 | SELECT | rs_concepto.Open "SELECt desc_concepto_asiento from cont_con… |
| FacturaB_COPIA.frm | 16450 | SELECT | rs_concepto.Open "SELECt desc_concepto_asiento from cont_con… |
| NotaCredDesc.frm | 4664 | SELECT | rs_concepto.Open "SELECt desc_concepto_asiento from cont_con… |
| NotaCred_COPIA.frm | 9064 | SELECT | rs_concepto.Open "SELECt desc_concepto_asiento from cont_con… |
| NotaCred_COPIA.frm | 12049 | SELECT | rs_concepto.Open "SELECt desc_concepto_asiento from cont_con… |
| Visualiza_TPV.frm | 9457 | SELECT | rs_concepto.Open "SELECt desc_concepto_asiento from cont_con… |
| Visualiza_TPV.frm | 10510 | SELECT | rs_concepto.Open "SELECt desc_concepto_asiento from cont_con… |
| TPV.frm | 19559 | SELECT | rs_concepto.Open "SELECt desc_concepto_asiento from cont_con… |
| TPV.frm | 20880 | SELECT | rs_concepto.Open "SELECt desc_concepto_asiento from cont_con… |
| TPV.frm | 25195 | SELECT | rs_concepto.Open "SELECt desc_concepto_asiento from cont_con… |
| TPV.frm | 25896 | SELECT | rs_concepto.Open "SELECt desc_concepto_asiento from cont_con… |
| Visualiza_NotaCredDesc.frm | 2441 | SELECT | rs_concepto.Open "SELECt desc_concepto_asiento from cont_con… |
| CargaMovCaja.frm | 4710 | SELECT | rs_concepto.Open "SELECt desc_concepto_asiento from cont_con… |
| OrdenPago.frm | 14907 | SELECT | rs_concepto.Open "SELECt desc_concepto_asiento from cont_con… |
| Imp_Carga.frm | 1334 | SELECT | rs_concepto.Open "SELECT desc_concepto_asiento from cont_con… |
| Visualiza_PNotaCred_Importe.frm | 4012 | SELECT | rs_concepto.Open "SELECt desc_concepto_asiento from cont_con… |
| Visualiza_FB_Copia.frm | 7520 | SELECT | rs_concepto.Open "SELECt desc_concepto_asiento from cont_con… |
| Visualiza_PNotaCredDev.frm | 5977 | SELECT | rs_concepto.Open "SELECt desc_concepto_asiento from cont_con… |
| Visualiza_PNotaCredDesc.frm | 3130 | SELECT | rs_concepto.Open "SELECt desc_concepto_asiento from cont_con… |
| FacturaB.frm | 18177 | SELECT | rs_concepto.Open "SELECt desc_concepto_asiento from cont_con… |
| FacturaB.frm | 22512 | SELECT | rs_concepto.Open "SELECt desc_concepto_asiento from cont_con… |
| Cont_ABMConceptos_Cont.frm | 478 | SELECT | Data_Concepto_Asiento.RecordSource = "select * from cont_con… |
| Cont_ABMConceptos_Cont.frm | 518 | SELECT | Data_Concepto_Asiento.RecordSource = "select * from cont_con… |
| CargaExtraccion.frm | 1477 | SELECT | rs_concepto.Open "SELECt desc_concepto_asiento from cont_con… |
| NotaCred_SinCompO.frm | 11429 | SELECT | rs_concepto.Open "SELECt desc_concepto_asiento from cont_con… |
| NotaCred_SinCompO.frm | 14343 | SELECT | rs_concepto.Open "SELECt desc_concepto_asiento from cont_con… |
| FacturaA.frm | 14226 | SELECT | rs_concepto.Open "SELECt desc_concepto_asiento from cont_con… |
| FacturaA.frm | 19122 | SELECT | rs_concepto.Open "SELECT desc_concepto_asiento from cont_con… |
| Visualiza_NotaDeb.frm | 4420 | SELECT | rs_concepto.Open "SELECt desc_concepto_asiento from cont_con… |
| PNotaDebCopia.frm | 4586 | SELECT | rs_concepto.Open "SELECt desc_concepto_asiento from cont_con… |
| NotaCred_Importe.frm | 6990 | SELECT | rs_concepto.Open "SELECt desc_concepto_asiento from cont_con… |
| CargaGastoBancario.frm | 2241 | SELECT | rs_concepto.Open "SELECt desc_concepto_asiento from cont_con… |
| Cont_ListaPA.frm | 661 | SELECT | rs_DatosConcepto.Open " SELECT * from cont_concepto_asiento … |
| Cont_ListaPA.frm | 756 | SELECT | rs_DatosConcepto.Open " SELECT * from cont_concepto_asiento … |
| Visualiza_FA.frm | 7360 | SELECT | rs_concepto.Open "SELECt desc_concepto_asiento from cont_con… |
| Inventario.frm | 2803 | SELECT | rs_concepto.Open "SELECt desc_concepto_asiento from cont_con… |
| Inventario.frm | 3477 | SELECT | rs_concepto.Open "SELECt desc_concepto_asiento from cont_con… |
| NotaCredCopia.frm | 9943 | SELECT | rs_concepto.Open "SELECt desc_concepto_asiento from cont_con… |
| NotaCredCopia.frm | 13217 | SELECT | rs_concepto.Open "SELECt desc_concepto_asiento from cont_con… |
| Visualiza_NotaCred_Importe.frm | 3499 | SELECT | rs_concepto.Open "SELECt desc_concepto_asiento from cont_con… |
| Visualiza_PNotaCred_ImporteCopia.frm | 3882 | SELECT | rs_concepto.Open "SELECt desc_concepto_asiento from cont_con… |
| Visualiza_FB.frm | 8055 | SELECT | rs_concepto.Open "SELECt desc_concepto_asiento from cont_con… |
| PFactura.frm | 9891 | SELECT | rs_concepto.Open "SELECt desc_concepto_asiento from cont_con… |
| CargaLiquidacionTC.frm | 3123 | SELECT | rs_concepto.Open "SELECt desc_concepto_asiento from cont_con… |
| NotaDeb.frm | 8492 | SELECT | rs_concepto.Open "SELECt desc_concepto_asiento from cont_con… |
| PNotaCredDesc.frm | 3062 | SELECT | rs_concepto.Open "SELECt desc_concepto_asiento from cont_con… |
| CargaClearing.frm | 1609 | SELECT | rs_concepto.Open "SELECT desc_concepto_asiento from cont_con… |
| CargaClearing.frm | 1631 | SELECT | rs_concepto.Open "SELECT desc_concepto_asiento from cont_con… |
| Visualiza_PFactura_Copia.frm | 7451 | SELECT | rs_concepto.Open "SELECt desc_concepto_asiento from cont_con… |
| PNotaCred_Importe.frm | 4355 | SELECT | rs_concepto.Open "SELECt desc_concepto_asiento from cont_con… |
| CargaTransBancaria.frm | 1675 | SELECT | rs_concepto.Open "SELECt desc_concepto_asiento from cont_con… |
| Cont_Carga_Concepto_Cont.frm | 242 | SELECT | rs_concepto_contable.Open "SELECT * FROM cont_concepto_asien… |
| Cont_Carga_Concepto_Cont.frm | 258 | SELECT | rs_concepto_contable.Open "SELECT * FROM cont_concepto_asien… |
| Cont_Carga_Concepto_Cont.frm | 271 | SELECT | rs_concepto_contable_anul.Open "SELECT * FROM cont_concepto_… |
| Cont_Carga_Concepto_Cont.frm | 292 | SELECT | Cont_ABMConceptos_Cont.Data_Concepto_Asiento.RecordSource = … |
| Cont_Carga_Concepto_Cont.frm | 303 | SELECT | rs_concepto_contable.Open "SELECT * FROM cont_concepto_asien… |
| Cont_Carga_Concepto_Cont.frm | 309 | SELECT | rs_concepto_contable_anul.Open "SELECT * FROM cont_concepto_… |
| Cont_Carga_Concepto_Cont.frm | 325 | SELECT | Cont_ABMConceptos_Cont.Data_Concepto_Asiento.RecordSource = … |
| Cont_ProcesosC.frm | 1364 | SELECT | rs_concepto.Open "SELECT desc_concepto_asiento from cont_con… |
| Cont_ProcesosC.frm | 2406 | SELECT | rs_concepto.Open "SELECT desc_concepto_asiento from cont_con… |
| Cont_ProcesosC.frm | 4694 | SELECT | rs_concepto.Open "SELECt desc_concepto_asiento from cont_con… |
| Visualiza_OrdenPagoC.frm | 10826 | SELECT | rs_concepto.Open "SELECt desc_concepto_asiento from cont_con… |
| Visualiza_NotaCredCopia.frm | 5526 | SELECT | rs_concepto.Open "SELECt desc_concepto_asiento from cont_con… |
| NotaCred.frm | 10527 | SELECT | rs_concepto.Open "SELECt desc_concepto_asiento from cont_con… |
| NotaCred.frm | 13801 | SELECT | rs_concepto.Open "SELECt desc_concepto_asiento from cont_con… |
| PNotaDeb.frm | 4812 | SELECT | rs_concepto.Open "SELECt desc_concepto_asiento from cont_con… |
| PNotaCredCopia.frm | 6954 | SELECT | rs_concepto.Open "SELECt desc_concepto_asiento from cont_con… |
| NotaDebCopia.frm | 8143 | SELECT | rs_concepto.Open "SELECt desc_concepto_asiento from cont_con… |
| CargaDeudaBancaria.frm | 2060 | SELECT | rs_concepto.Open "SELECT desc_concepto_asiento from cont_con… |
| CargaDNF_Caja.frm | 1649 | SELECT | rs_concepto.Open "SELECT desc_concepto_asiento from cont_con… |
| ReciboCobro.frm | 16748 | SELECT | rs_concepto.Open "SELECt desc_concepto_asiento from cont_con… |
| … | … | … | *(15 referencias más)* |

---

## 4. Uso en Synap (reports)

*No se encontraron referencias en el módulo reports.*

[← Índice de tablas](../DB_INDICE_TABLAS.md)