# Tabla `cont_asiento`

Base: **administranet**

---

## 1. Schema (information_schema)

### 1.1 Columnas

| Campo | Tipo | Nulo | PK | FK | Referencia |
|-------|------|------|----|----|------------|
| id_asiento | DOUBLE | No | ✓ |  |  |
| nro_asiento | DOUBLE | Sí |  |  |  |
| fecha_asiento | DATE | Sí |  |  |  |
| id_ejercicio | DOUBLE | Sí |  |  |  |
| id_periodo | DOUBLE | Sí |  |  |  |
| codigo_movimiento | DECIMAL | Sí |  |  |  |
| codigo_movimiento_anul | DECIMAL | Sí |  |  |  |
| debe_asiento | DECIMAL | Sí |  |  |  |
| haber_asiento | DECIMAL | Sí |  |  |  |
| saldo_asiento | DECIMAL | Sí |  |  |  |
| id_pc | DOUBLE | Sí |  |  |  |
| desc_renglon_asiento | VARCHAR | Sí |  |  |  |
| desc_concepto_asiento | VARCHAR | Sí |  |  |  |
| id_concepto_asiento | DOUBLE | Sí |  |  |  |
| balanceado_asiento | VARCHAR | Sí |  |  |  |
| id_usuario | DOUBLE | Sí |  |  |  |
| desc_asiento | VARCHAR | Sí |  |  |  |
| tipo_asiento | VARCHAR | Sí |  |  |  |
| anulado | VARCHAR | Sí |  |  |  |
| id_pa | DOUBLE | Sí |  |  |  |
| codigo_movimiento_anul_cv | DOUBLE | Sí |  |  |  |

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
| CargaBDeposito.frm | 2609 | SELECT | rs_newasiento.Open "SELECT * from cont_asiento  WHERE id_asi… |
| CargaBDeposito.frm | 2917 | SELECT | "From cont_asiento " & _ |
| PNotaCred.frm | 6994 | SELECT | rs_newasiento.Open "SELECT * from cont_asiento WHERE id_asie… |
| PNotaCred.frm | 7356 | SELECT | "From cont_asiento where codigo_movimiento = " & contador & … |
| PNotaCred.frm | 7370 | SELECT | "From cont_asiento " & _ |
| PNotaCred.frm | 7390 | SELECT | "From cont_asiento " & _ |
| PNotaCred.frm | 7436 | SELECT | "From cont_asiento " & _ |
| Visualiza_ReciboCobro.frm | 15436 | SELECT | rs_newasiento.Open "SELECT * from cont_asiento", conn, adOpe… |
| Visualiza_ReciboCobro.frm | 15799 | SELECT | "From cont_asiento " & _ |
| Visualiza_NotaCred.frm | 5595 | SELECT | rs_newasiento.Open "SELECT * from cont_asiento", conn, adOpe… |
| Visualiza_NotaCred.frm | 5907 | SELECT | "From cont_asiento where codigo_movimiento = " & contador & … |
| Visualiza_NotaCred.frm | 5921 | SELECT | "From cont_asiento " & _ |
| Visualiza_NotaCred.frm | 5941 | SELECT | "From cont_asiento " & _ |
| Visualiza_NotaCred.frm | 5987 | SELECT | "From cont_asiento " & _ |
| Visualiza_CargaMovStock.frm | 5376 | SELECT | rs_newasiento.Open "SELECT * from cont_asiento WHERE id_asie… |
| Visualiza_CargaMovStock.frm | 5684 | SELECT | "From cont_asiento " & _ |
| NotaCredCon.frm | 7336 | SELECT | rs_newasiento.Open "SELECT * from cont_asiento WHERE id_asie… |
| NotaCredCon.frm | 7661 | SELECT | "From cont_asiento " & _ |
| Visualiza_PNotaDeb.frm | 3855 | SELECT | rs_newasiento.Open "SELECT * from cont_asiento", conn, adOpe… |
| Visualiza_PNotaDeb.frm | 4169 | SELECT | "From cont_asiento " & _ |
| FacturaB_COPIA.frm | 12085 | SELECT | rs_newasiento.Open "SELECT * from cont_asiento  WHERE id_asi… |
| FacturaB_COPIA.frm | 12453 | SELECT | "From cont_asiento where codigo_movimiento = " & contador & … |
| FacturaB_COPIA.frm | 12468 | SELECT | "From cont_asiento " & _ |
| FacturaB_COPIA.frm | 12488 | SELECT | "From cont_asiento " & _ |
| FacturaB_COPIA.frm | 12534 | SELECT | "From cont_asiento " & _ |
| FacturaB_COPIA.frm | 16236 | SELECT | rs_newasiento.Open "SELECT * from cont_asiento WHERE id_asie… |
| NotaCredDesc.frm | 4419 | SELECT | rs_newasiento.Open "SELECT * from cont_asiento WHERE id_asie… |
| NotaCredDesc.frm | 4733 | SELECT | "From cont_asiento " & _ |
| NotaCred_COPIA.frm | 8819 | SELECT | rs_newasiento.Open "SELECT * from cont_asiento WHERE id_asie… |
| NotaCred_COPIA.frm | 9140 | SELECT | "From cont_asiento where codigo_movimiento = " & contador & … |
| NotaCred_COPIA.frm | 9154 | SELECT | "From cont_asiento " & _ |
| NotaCred_COPIA.frm | 9174 | SELECT | "From cont_asiento " & _ |
| NotaCred_COPIA.frm | 9220 | SELECT | "From cont_asiento " & _ |
| NotaCred_COPIA.frm | 11832 | SELECT | rs_newasiento.Open "SELECT * from cont_asiento WHERE id_asie… |
| Visualiza_TPV.frm | 9214 | SELECT | rs_newasiento.Open "SELECT * from cont_asiento", conn, adOpe… |
| Visualiza_TPV.frm | 10269 | SELECT | rs_newasiento.Open "SELECT * from cont_asiento", conn, adOpe… |
| ChequeTercero.frm | 2750 | SELECT | rs_EstaAnul.Open "SELECT * from cont_asiento where Codigo_Mo… |
| ChequeTercero.frm | 2816 | SELECT | rs_anul.Open "select * from cont_asiento where Codigo_Movimi… |
| ChequeTercero.frm | 2839 | SELECT | rs_ContraAsiento.Open "select * from cont_asiento where Codi… |
| TPV.frm | 19316 | SELECT | rs_newasiento.Open "SELECT * from cont_asiento WHERE id_asie… |
| TPV.frm | 20639 | SELECT | rs_newasiento.Open "SELECT * from cont_asiento WHERE id_asie… |
| TPV.frm | 24981 | SELECT | rs_newasiento.Open "SELECT * from cont_asiento WHERE id_asie… |
| TPV.frm | 25679 | SELECT | rs_newasiento.Open "SELECT * from cont_asiento WHERE id_asie… |
| TPV.frm | 25954 | SELECT | "From cont_asiento where codigo_movimiento = " & contador & … |
| TPV.frm | 25969 | SELECT | "From cont_asiento " & _ |
| TPV.frm | 25989 | SELECT | "From cont_asiento " & _ |
| Cont_ProcAsientosM.frm | 1053 | SELECT | DataListaAsiento.RecordSource = "SELECT DISTINCT nro_asiento… |
| Cont_ProcAsientosM.frm | 1058 | SELECT | DataListaAsiento.RecordSource = "SELECT DISTINCT nro_asiento… |
| Cont_ProcAsientosM.frm | 1065 | SELECT | "FROM cont_asiento WHERE " & _ |
| Cont_ProcAsientosM.frm | 1288 | SELECT | rs_visualizar.Open "SELECT * from cont_asiento where codigo_… |
| Cont_ProcAsientosM.frm | 1447 | SELECT | '            DataAsiento.RecordSource = "SELECT cont_asiento… |
| Cont_ProcAsientosM.frm | 1453 | SELECT | "FROM cont_asiento " & _ |
| Cont_ProcAsientosM.frm | 1502 | SELECT | '        DataListaAsiento.RecordSource = "SELECT DISTINCT nr… |
| Cont_ProcAsientosM.frm | 1511 | SELECT | '        DataListaAsiento.RecordSource = "SELECT DISTINCT nr… |
| Cont_ProcAsientosM.frm | 1519 | SELECT | '        DataListaAsiento.RecordSource = "SELECT DISTINCT nr… |
| Cont_ProcAsientosM.frm | 1527 | SELECT | '        DataListaAsiento.RecordSource = "SELECT DISTINCT nr… |
| Cont_ProcAsientosM.frm | 1538 | SELECT | '        DataListaAsiento.RecordSource = "SELECT DISTINCT nr… |
| Cont_ProcAsientosM.frm | 1547 | SELECT | '        DataListaAsiento.RecordSource = "SELECT DISTINCT nr… |
| Cont_ProcAsientosM.frm | 1555 | SELECT | '        DataListaAsiento.RecordSource = "SELECT DISTINCT nr… |
| Cont_ProcAsientosM.frm | 1563 | SELECT | '        DataListaAsiento.RecordSource = "SELECT DISTINCT nr… |
| Cont_ProcAsientosM.frm | 1581 | SELECT | '    DataAsiento.RecordSource = "SELECT * from cont_asiento … |
| Cont_ProcAsientosM.frm | 1629 | SELECT | DataListaAsiento.RecordSource = "SELECT DISTINCT nro_asiento… |
| Cont_ProcAsientosM.frm | 1639 | SELECT | DataListaAsiento.RecordSource = "SELECT DISTINCT nro_asiento… |
| Cont_ProcAsientosM.frm | 1648 | SELECT | DataListaAsiento.RecordSource = "SELECT DISTINCT nro_asiento… |
| Cont_ProcAsientosM.frm | 1657 | SELECT | DataListaAsiento.RecordSource = "SELECT DISTINCT nro_asiento… |
| Cont_ProcAsientosM.frm | 1669 | SELECT | DataListaAsiento.RecordSource = "SELECT DISTINCT nro_asiento… |
| Cont_ProcAsientosM.frm | 1679 | SELECT | DataListaAsiento.RecordSource = "SELECT DISTINCT nro_asiento… |
| Cont_ProcAsientosM.frm | 1688 | SELECT | DataListaAsiento.RecordSource = "SELECT DISTINCT nro_asiento… |
| Cont_ProcAsientosM.frm | 1697 | SELECT | DataListaAsiento.RecordSource = "SELECT DISTINCT nro_asiento… |
| Cont_ProcAsientosM.frm | 1721 | SELECT | DataAsiento.RecordSource = "SELECT * from cont_asiento " & _ |
| Cont_ProcAsientosM.frm | 1929 | SELECT | rs_anul.Open "select * from cont_asiento where Codigo_Movimi… |
| Cont_ProcAsientosM.frm | 1952 | SELECT | rs_ContraAsiento.Open "select * from cont_asiento where Codi… |
| Cont_ProcAsientosM.frm | 2250 | SELECT | DataListaAsiento.RecordSource = "SELECT DISTINCT nro_asiento… |
| Visualiza_NotaCredDesc.frm | 2200 | SELECT | rs_newasiento.Open "SELECT * from cont_asiento", conn, adOpe… |
| Visualiza_NotaCredDesc.frm | 2510 | SELECT | "From cont_asiento " & _ |
| CuentaCliente.frm | 3454 | SELECT | rs_EstaAnul.Open "SELECT * from cont_asiento where Codigo_Mo… |
| CuentaCliente.frm | 3520 | SELECT | rs_anul.Open "select * from cont_asiento where Codigo_Movimi… |
| CuentaCliente.frm | 3543 | SELECT | rs_ContraAsiento.Open "select * from cont_asiento where Codi… |
| CargaMovCaja.frm | 4465 | SELECT | rs_newasiento.Open "SELECT * from cont_asiento  WHERE id_asi… |
| CargaMovCaja.frm | 4771 | SELECT | "From cont_asiento " & _ |
| … | … | … | *(300 referencias más)* |

---

## 4. Uso en Synap (reports)

*No se encontraron referencias en el módulo reports.*

[← Índice de tablas](../DB_INDICE_TABLAS.md)