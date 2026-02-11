# Tabla `descuento_op_nctemp`

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
| CodUsuario | INT | No |  |  |  |
| Seleccionado | VARCHAR | No |  |  |  |
| id_descuento_op_nctemp | DOUBLE | No | ✓ |  |  |

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
| Visualiza_PNotaCredDesc.frm | 1568 | SELECT | DataDescOPTemp.RecordSource = "select * from Descuento_OP_NC… |
| Visualiza_PNotaCredDesc.frm | 1611 | SELECT | DataDescOPTemp.RecordSource = "select * from Descuento_OP_NC… |
| Visualiza_PNotaCredDesc.frm | 1619 | SELECT | rs_ConsDescOP.Open "select sum(importe) as SumaImporte from … |
| Visualiza_PNotaCredDesc.frm | 2117 | SELECT | rs_ConsDescOP.Open "select sum(importe) as SumaImporte from … |
| PNotaCredDesc.frm | 1410 | SELECT | DataDescOPTemp.RecordSource = "select * from Descuento_OP_NC… |
| PNotaCredDesc.frm | 1453 | SELECT | DataDescOPTemp.RecordSource = "select * from Descuento_OP_NC… |
| PNotaCredDesc.frm | 1465 | SELECT | rs_ConsDescOP.Open "select sum(importe) as SumaImporte from … |
| PNotaCredDesc.frm | 2037 | SELECT | rs_ConsDescOP.Open "select sum(importe) as SumaImporte from … |
| Principal.frm | 6080 | SELECT | conn.Execute "delete from descuento_op_nctemp where Codusuar… |
| Principal.frm | 6080 | DELETE | conn.Execute "delete from descuento_op_nctemp where Codusuar… |
| Principal.frm | 6146 | SELECT | conn.Execute "delete from descuento_op_nctemp where Codusuar… |
| Principal.frm | 6146 | DELETE | conn.Execute "delete from descuento_op_nctemp where Codusuar… |

---

## 4. Uso en Synap (reports)

*No se encontraron referencias en el módulo reports.*

[← Índice de tablas](../DB_INDICE_TABLAS.md)