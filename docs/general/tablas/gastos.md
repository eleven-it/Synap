# Tabla `gastos`

Base: **administranet**

---

## 1. Schema (information_schema)

### 1.1 Columnas

| Campo | Tipo | Nulo | PK | FK | Referencia |
|-------|------|------|----|----|------------|
| Codigo | INT | No | ✓ |  |  |
| Nombre | VARCHAR | Sí |  |  |  |
| TipoIVA | VARCHAR | No |  |  |  |
| CodIVA | INT | No |  |  |  |
| anulado | VARCHAR | Sí |  |  |  |
| moneda | VARCHAR | Sí |  |  |  |
| id_pc | DOUBLE | Sí |  |  |  |
| id_gastos_grupo | BIGINT | Sí |  |  |  |

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
| NotaCredCon.frm | 5913 | SELECT | DataGastos.RecordSource = "select * from gastos WHERE anulad… |
| NotaCredCon.frm | 6684 | SELECT | rs_vect.Open "SELECT * FROM gastos WHERE codigo = " & data_o… |
| Visualiza_PNotaDeb.frm | 2146 | SELECT | DataGasto.RecordSource = "SELECT codigo, nombre, id_pc FROM … |
| FacturaB_COPIA.frm | 16023 | SELECT | '                            rs_Gasto.Open "SELECT id_pc fro… |
| NotaCred_COPIA.frm | 11515 | SELECT | '                            rs_Gasto.Open "SELECT id_pc fro… |
| TPV.frm | 24768 | SELECT | '                            rs_Gasto.Open "SELECT id_pc fro… |
| TPV.frm | 25360 | SELECT | '                            rs_Gasto.Open "SELECT id_pc fro… |
| OrdenPago.frm | 10298 | SELECT | DataGastos.RecordSource = "select * from gastos WHERE anulad… |
| OrdenPago.frm | 13084 | SELECT | rs_vect.Open "SELECT * from gastos where codigo = " & data_o… |
| FacturaB.frm | 22082 | SELECT | '                            rs_Gasto.Open "SELECT id_pc fro… |
| FacturaA.frm | 18692 | SELECT | '                            rs_Gasto.Open "SELECT id_pc fro… |
| PNotaDebCopia.frm | 2395 | SELECT | DataGasto.RecordSource = "SELECT codigo, nombre, id_pc FROM … |
| NotaCredCopia.frm | 12683 | SELECT | '                            rs_Gasto.Open "SELECT id_pc fro… |
| PFactura.frm | 8786 | SELECT | rs_Gasto.Open "SELECT id_pc from gastos where codigo = " & r… |
| AltaGastos.frm | 508 | SELECT | " FROM gastos  " & _ |
| Visualiza_PFactura_Copia.frm | 6454 | SELECT | rs_Gasto.Open "SELECT id_pc from gastos where codigo = " & r… |
| Visualiza_OrdenPagoC.frm | 7342 | SELECT | DataGastos.RecordSource = "select * from gastos WHERE anulad… |
| Visualiza_OrdenPagoC.frm | 9304 | SELECT | rs_vect.Open "SELECT * from gastos where codigo = " & data_o… |
| NotaCred.frm | 13267 | SELECT | '                            rs_Gasto.Open "SELECT id_pc fro… |
| PNotaDeb.frm | 2578 | SELECT | DataGasto.RecordSource = "SELECT codigo, nombre, id_pc FROM … |
| CargaDNF_Caja.frm | 704 | SELECT | DataGasto.RecordSource = "select * from Gastos WHERE anulado… |
| CargaDNF_Caja.frm | 1216 | SELECT | rs_Gasto.Open "SELECT id_pc from gastos where codigo = " & I… |
| En_CargaOE_Ref.frm | 1157 | SELECT | "From Gastos Where anulado = 'No' " |
| Visualiza_PFacturaCopia2.frm | 6593 | SELECT | rs_Gasto.Open "SELECT id_pc from gastos where codigo = " & r… |
| Visualiza_PFactura.frm | 6810 | SELECT | rs_Gasto.Open "SELECT id_pc from gastos where codigo = " & r… |
| Visualiza_NotaCredCon.frm | 5403 | SELECT | DataGastos.RecordSource = "select * from gastos WHERE anulad… |
| Visualiza_NotaCredCon.frm | 6163 | SELECT | rs_vect.Open "SELECT * FROM gastos WHERE codigo = " & data_o… |
| CargaGasto.frm | 797 | SELECT | rs_Gasto.Open "SELECT * FROM gastos WHERE Codigo = 0", conn,… |
| CargaGasto.frm | 935 | SELECT | rs_Gasto.Open "SELECT * FROM gastos WHERE Codigo = " & ABMGa… |
| Caja.frm | 1069 | SELECT | 'DataGasto.RecordSource = "select * from gastos where Codigo… |
| TPV_2.frm | 22801 | SELECT | '                            rs_Gasto.Open "SELECT id_pc fro… |
| TPV_2.frm | 23393 | SELECT | '                            rs_Gasto.Open "SELECT id_pc fro… |
| Visualiza_OrdenPago.frm | 7634 | SELECT | DataGastos.RecordSource = "select * from gastos WHERE anulad… |
| Visualiza_OrdenPago.frm | 9706 | SELECT | rs_vect.Open "SELECT * from gastos where codigo = " & data_o… |

---

## 4. Uso en Synap (reports)

| Archivo | Línea | Operación | Fragmento |
|---------|-------|-----------|-----------|
| services/query_runner.py | 1465 | JOIN | LEFT JOIN gastos g ON g.Codigo = c.cod_gasto |

[← Índice de tablas](../DB_INDICE_TABLAS.md)