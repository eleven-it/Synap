# Tabla `cont_periodo`

Base: **administranet**

---

## 1. Schema (information_schema)

### 1.1 Columnas

| Campo | Tipo | Nulo | PK | FK | Referencia |
|-------|------|------|----|----|------------|
| id_periodo | DOUBLE | No | ✓ |  |  |
| id_ejercicio | DOUBLE | Sí |  |  |  |
| fecdesde_periodo | DATE | Sí |  |  |  |
| fechasta_periodo | DATE | Sí |  |  |  |
| activo_periodo | VARCHAR | Sí |  |  |  |
| descripcion_periodo | VARCHAR | Sí |  |  |  |
| id_pc | DOUBLE | Sí |  |  |  |
| cerrado | VARCHAR | Sí |  |  |  |

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
| CargaBDeposito.frm | 2583 | SELECT | rs_periodo.Open "Select * from cont_periodo where id_periodo… |
| CargaBDeposito.frm | 2585 | SELECT | rs_periodo.Open "Select * from cont_periodo where activo_per… |
| CargaBDeposito.frm | 2808 | SELECT | rs_periodo.Open "Select * from cont_periodo where activo_per… |
| PNotaCred.frm | 6968 | SELECT | rs_periodo.Open "Select * from cont_periodo where id_periodo… |
| PNotaCred.frm | 6970 | SELECT | rs_periodo.Open "Select * from cont_periodo where activo_per… |
| PNotaCred.frm | 7202 | SELECT | rs_periodo.Open "Select * from cont_periodo where activo_per… |
| Visualiza_ReciboCobro.frm | 15422 | SELECT | rs_periodo.Open "Select * from cont_periodo where activo_per… |
| Visualiza_ReciboCobro.frm | 15631 | SELECT | rs_periodo.Open "Select * from cont_periodo where activo_per… |
| Visualiza_NotaCred.frm | 5581 | SELECT | rs_periodo.Open "Select * from cont_periodo where activo_per… |
| Visualiza_NotaCred.frm | 5790 | SELECT | rs_periodo.Open "Select * from cont_periodo where activo_per… |
| Cont_CargaPlanCta.frm | 777 | SELECT | rs_periodo.Open "Select DISTINCT id_periodo from cont_period… |
| Visualiza_CargaMovStock.frm | 5362 | SELECT | rs_periodo.Open "Select * from cont_periodo where activo_per… |
| Visualiza_CargaMovStock.frm | 5570 | SELECT | rs_periodo.Open "Select * from cont_periodo where activo_per… |
| NotaCredCon.frm | 7310 | SELECT | rs_periodo.Open "Select * from cont_periodo where id_periodo… |
| NotaCredCon.frm | 7312 | SELECT | rs_periodo.Open "Select * from cont_periodo where activo_per… |
| NotaCredCon.frm | 7535 | SELECT | rs_periodo.Open "Select * from cont_periodo where activo_per… |
| Visualiza_PNotaDeb.frm | 3841 | SELECT | rs_periodo.Open "Select * from cont_periodo where activo_per… |
| Visualiza_PNotaDeb.frm | 4050 | SELECT | rs_periodo.Open "Select * from cont_periodo where activo_per… |
| FacturaB_COPIA.frm | 12059 | SELECT | rs_periodo.Open "Select * from cont_periodo where id_periodo… |
| FacturaB_COPIA.frm | 12061 | SELECT | rs_periodo.Open "Select * from cont_periodo where activo_per… |
| FacturaB_COPIA.frm | 12291 | SELECT | rs_periodo.Open "Select * from cont_periodo where activo_per… |
| NotaCredDesc.frm | 4393 | SELECT | rs_periodo.Open "Select * from cont_periodo where id_periodo… |
| NotaCredDesc.frm | 4395 | SELECT | rs_periodo.Open "Select * from cont_periodo where activo_per… |
| NotaCredDesc.frm | 4618 | SELECT | rs_periodo.Open "Select * from cont_periodo where activo_per… |
| NotaCred_COPIA.frm | 8793 | SELECT | rs_periodo.Open "Select * from cont_periodo where id_periodo… |
| NotaCred_COPIA.frm | 8795 | SELECT | rs_periodo.Open "Select * from cont_periodo where activo_per… |
| NotaCred_COPIA.frm | 9018 | SELECT | rs_periodo.Open "Select * from cont_periodo where activo_per… |
| Visualiza_TPV.frm | 9200 | SELECT | rs_periodo.Open "Select * from cont_periodo where activo_per… |
| Visualiza_TPV.frm | 9409 | SELECT | rs_periodo.Open "Select * from cont_periodo where activo_per… |
| Visualiza_TPV.frm | 10255 | SELECT | rs_periodo.Open "Select * from cont_periodo where activo_per… |
| Visualiza_TPV.frm | 10464 | SELECT | rs_periodo.Open "Select * from cont_periodo where activo_per… |
| ChequeTercero.frm | 2885 | SELECT | rs_periodo.Open "Select * from cont_periodo where activo_per… |
| Cont_CargaPerido.frm | 441 | SELECT | rs_activo.Open "Select * from cont_periodo where activo_peri… |
| Cont_CargaPerido.frm | 464 | SELECT | rs_periodo.Open "select * from cont_periodo where id_ejercic… |
| Cont_CargaPerido.frm | 478 | SELECT | rs_periodo.Open "select * from cont_periodo where id_ejercic… |
| Cont_CargaPerido.frm | 546 | SELECT | Cont_AbmEjercicio.DataPeriodo.RecordSource = "SELECT * FROM … |
| Cont_CargaPerido.frm | 566 | SELECT | rs_periodo.Open "SELECT * FROM cont_periodo WHERE id_periodo… |
| Cont_CargaPerido.frm | 576 | SELECT | rs_ValidoPer.Open "select * from cont_periodo where id_ejerc… |
| Cont_CargaPerido.frm | 598 | SELECT | rs_ValidoPer.Open "select * from cont_periodo where id_ejerc… |
| Cont_CargaPerido.frm | 622 | SELECT | rs_activo.Open "Select * from cont_periodo where activo_peri… |
| TPV.frm | 19293 | SELECT | rs_periodo.Open "Select * from cont_periodo where activo_per… |
| TPV.frm | 19511 | SELECT | rs_periodo.Open "Select * from cont_periodo where activo_per… |
| TPV.frm | 20616 | SELECT | rs_periodo.Open "Select * from cont_periodo where activo_per… |
| TPV.frm | 20834 | SELECT | rs_periodo.Open "Select * from cont_periodo where activo_per… |
| Cont_ProcAsientosM.frm | 1024 | SELECT | rs_periodo.Open "Select * from cont_periodo where activo_per… |
| Cont_ProcAsientosM.frm | 1310 | SELECT | rs_periodo.Open "Select * from cont_periodo where activo_per… |
| Cont_ProcAsientosM.frm | 1830 | SELECT | rs_cerrado.Open "SELECT cerrado from cont_periodo WHERE id_p… |
| Cont_ProcAsientosM.frm | 2005 | SELECT | rs_periodo.Open "Select * from cont_periodo where activo_per… |
| Visualiza_NotaCredDesc.frm | 2186 | SELECT | rs_periodo.Open "Select * from cont_periodo where activo_per… |
| Visualiza_NotaCredDesc.frm | 2395 | SELECT | rs_periodo.Open "Select * from cont_periodo where activo_per… |
| CuentaCliente.frm | 3589 | SELECT | rs_periodo.Open "Select * from cont_periodo where activo_per… |
| CargaMovCaja.frm | 4439 | SELECT | rs_periodo.Open "Select * from cont_periodo where id_periodo… |
| CargaMovCaja.frm | 4441 | SELECT | rs_periodo.Open "Select * from cont_periodo where activo_per… |
| CargaMovCaja.frm | 4664 | SELECT | rs_periodo.Open "Select * from cont_periodo where activo_per… |
| OrdenPago.frm | 14627 | SELECT | rs_periodo.Open "Select * from cont_periodo where id_periodo… |
| OrdenPago.frm | 14629 | SELECT | rs_periodo.Open "Select * from cont_periodo where activo_per… |
| OrdenPago.frm | 14857 | SELECT | rs_periodo.Open "Select * from cont_periodo where activo_per… |
| Imp_Carga.frm | 465 | SELECT | rs_periodo.Open "SELECT * FROM cont_periodo WHERE id_periodo… |
| Imp_Carga.frm | 468 | SELECT | rs_periodo.Open "Select * from cont_periodo where activo_per… |
| Imp_Carga.frm | 1071 | SELECT | rs_periodo.Open "Select * from cont_periodo where activo_per… |
| Imp_Carga.frm | 1288 | SELECT | rs_periodo.Open "Select * from cont_periodo where activo_per… |
| Visualiza_PNotaCred_Importe.frm | 3755 | SELECT | rs_periodo.Open "Select * from cont_periodo where activo_per… |
| Visualiza_PNotaCred_Importe.frm | 3964 | SELECT | rs_periodo.Open "Select * from cont_periodo where activo_per… |
| Visualiza_FB_Copia.frm | 7266 | SELECT | rs_periodo.Open "Select * from cont_periodo where activo_per… |
| Visualiza_FB_Copia.frm | 7474 | SELECT | rs_periodo.Open "Select * from cont_periodo where activo_per… |
| Visualiza_PNotaCredDev.frm | 5720 | SELECT | rs_periodo.Open "Select * from cont_periodo where activo_per… |
| Visualiza_PNotaCredDev.frm | 5929 | SELECT | rs_periodo.Open "Select * from cont_periodo where activo_per… |
| Visualiza_PNotaCredDesc.frm | 2873 | SELECT | rs_periodo.Open "Select * from cont_periodo where activo_per… |
| Visualiza_PNotaCredDesc.frm | 3082 | SELECT | rs_periodo.Open "Select * from cont_periodo where activo_per… |
| FacturaB.frm | 17898 | SELECT | rs_periodo.Open "Select * from cont_periodo where id_periodo… |
| FacturaB.frm | 17900 | SELECT | rs_periodo.Open "Select * from cont_periodo where activo_per… |
| FacturaB.frm | 18131 | SELECT | rs_periodo.Open "Select * from cont_periodo where activo_per… |
| CargaExtraccion.frm | 1206 | SELECT | rs_periodo.Open "Select * from cont_periodo where id_periodo… |
| CargaExtraccion.frm | 1208 | SELECT | rs_periodo.Open "Select * from cont_periodo where activo_per… |
| CargaExtraccion.frm | 1431 | SELECT | rs_periodo.Open "Select * from cont_periodo where activo_per… |
| NotaCred_SinCompO.frm | 11158 | SELECT | rs_periodo.Open "Select * from cont_periodo where id_periodo… |
| NotaCred_SinCompO.frm | 11160 | SELECT | rs_periodo.Open "Select * from cont_periodo where activo_per… |
| NotaCred_SinCompO.frm | 11383 | SELECT | rs_periodo.Open "Select * from cont_periodo where activo_per… |
| FacturaA.frm | 13953 | SELECT | rs_periodo.Open "Select * from cont_periodo where id_periodo… |
| FacturaA.frm | 13955 | SELECT | rs_periodo.Open "Select * from cont_periodo where activo_per… |
| … | … | … | *(162 referencias más)* |

---

## 4. Uso en Synap (reports)

*No se encontraron referencias en el módulo reports.*

[← Índice de tablas](../DB_INDICE_TABLAS.md)