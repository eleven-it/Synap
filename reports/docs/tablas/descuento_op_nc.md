# Tabla `descuento_op_nc`

Base: **administranet**

---

## 1. Schema (information_schema)

### 1.1 Columnas

| Campo | Tipo | Nulo | PK | FK | Referencia |
|-------|------|------|----|----|------------|
| Fecha | DATE | No |  |  |  |
| CodDescuento | INT | No |  |  |  |
| NroOP | VARCHAR | No |  |  |  |
| CodigoMovimiento | DECIMAL | No |  |  |  |
| Importe | DECIMAL | No |  |  |  |
| Porcentaje | DECIMAL | No |  |  |  |
| CodProveedor | INT | No |  |  |  |
| NroNC | VARCHAR | No |  |  |  |
| Computado | VARCHAR | No |  |  |  |
| id_descuento_op_nc | INT | No | ✓ |  |  |
| Anulado | VARCHAR | Sí |  |  |  |

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
| OrdenPago.frm | 7847 | SELECT | rs_descuento_op_nc.Open "SELECT * FROM descuento_op_nc WHERE… |
| Visualiza_PNotaCredDesc.frm | 1582 | SELECT | rs_DescOP.Open "select * from Descuento_OP_NC where " & _ |
| Visualiza_PNotaCredDesc.frm | 1988 | SELECT | DataConsDescOP.RecordSource = "select * from Descuento_OP_NC… |
| ConsultaComprobante.frm | 13357 | SELECT | rs_descuento_op_nc.Open "SELECT * FROM descuento_op_nc WHERE… |
| ConsultaComprobante.frm | 20349 | SELECT | rs_descuento_op_nc.Open "SELECT * FROM descuento_op_nc WHERE… |
| PNotaCredDesc.frm | 1424 | SELECT | rs_DescOP.Open "select * from descuento_op_nc where " & _ |
| PNotaCredDesc.frm | 1889 | SELECT | DataConsDescOP.RecordSource = "select * from Descuento_OP_NC… |
| trz_trazabilidadComp.frm | 3874 | SELECT | Visualiza_PNotaCredDesc.DataDescOPTemp.RecordSource = "selec… |
| trz_trazabilidadComp.frm | 4934 | SELECT | rs_descuento_op_nc.Open "SELECT * FROM descuento_op_nc WHERE… |
| CargaComprobantesP.frm | 3188 | SELECT | DataDescOP.RecordSource = " Select * from descuento_op_nc  w… |
| CuentaProveedor.frm | 1464 | SELECT | '        rs_descuento_op_nc.Open "SELECT * FROM descuento_op… |
| CuentaProveedor.frm | 2614 | SELECT | Visualiza_PNotaCredDesc.DataDescOPTemp.RecordSource = "selec… |
| Visualiza.bas | 5328 | SELECT | Visualiza_PNotaCredDesc.DataDescOPTemp.RecordSource = "selec… |
| Visualiza.bas | 7598 | SELECT | rs_descuento_op_nc.Open "SELECT * FROM descuento_op_nc WHERE… |

---

## 4. Uso en Synap (reports)

*No se encontraron referencias en el módulo reports.*

[← Índice de tablas](../DB_INDICE_TABLAS.md)