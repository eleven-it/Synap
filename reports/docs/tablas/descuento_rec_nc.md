# Tabla `descuento_rec_nc`

Base: **administranet**

---

## 1. Schema (information_schema)

### 1.1 Columnas

| Campo | Tipo | Nulo | PK | FK | Referencia |
|-------|------|------|----|----|------------|
| id_descuento_rec_nc | DOUBLE | No | ✓ |  |  |
| Fecha | DATE | No |  |  |  |
| CodDescuento | INT | No |  |  |  |
| NroREC | VARCHAR | No |  |  |  |
| CodigoMovimiento | DECIMAL | No |  |  |  |
| Importe | DECIMAL | No |  |  |  |
| Porcentaje | DECIMAL | No |  |  |  |
| CodCliente | INT | No |  |  |  |
| NroNC | VARCHAR | No |  |  |  |
| Computado | VARCHAR | No |  |  |  |
| Anulado | VARCHAR | No |  |  |  |
| Seleccionado | VARCHAR | No |  |  |  |
| utilizado | VARCHAR | Sí |  |  |  |

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
| Visualiza_ReciboCobro.frm | 7497 | SELECT | rs_descuento_rec_nc.Open "SELECT * FROM descuento_rec_nc whe… |
| Visualiza_ReciboCobro.frm | 12073 | SELECT | '        NotaCredDesc.DataDescREC.RecordSource = "select * f… |
| NotaCredDesc.frm | 1353 | UPDATE | conn.Execute "UPDATE descuento_rec_nc SET seleccionado = 'Si… |
| NotaCredDesc.frm | 1356 | UPDATE | conn.Execute "UPDATE descuento_rec_nc SET utilizado = 'Si' W… |
| NotaCredDesc.frm | 1409 | SELECT | DataDescRec.RecordSource = "select * from descuento_rec_nc w… |
| NotaCredDesc.frm | 1461 | SELECT | DataConsDescRec.RecordSource = "select sum(importe) as SumaI… |
| NotaCredDesc.frm | 2520 | SELECT | rs_descuento_rec_nc.Open "SELECT * FROM descuento_rec_nc WHE… |
| NotaCredDesc.frm | 2577 | UPDATE | conn.Execute "UPDATE descuento_rec_nc SET utilizado = 'No' W… |
| NotaCredDesc.frm | 3613 | UPDATE | conn.Execute "UPDATE descuento_rec_nc SET utilizado = 'No' W… |
| NotaCredDesc.frm | 3682 | SELECT | rs_consDesc.Open "select sum(importe) as SumaImporte from De… |
| NotaCredDesc.frm | 3740 | UPDATE | conn.Execute "UPDATE descuento_rec_nc SET utilizado = 'No' W… |
| Visualiza_NotaCredDesc.frm | 1465 | UPDATE | conn.Execute "UPDATE descuento_rec_nc SET seleccionado = 'Si… |
| Visualiza_NotaCredDesc.frm | 1468 | UPDATE | conn.Execute "UPDATE descuento_rec_nc SET utilizado = 'Si' W… |
| Visualiza_NotaCredDesc.frm | 1488 | SELECT | DataDescRec.RecordSource = "select * from descuento_rec_nc w… |
| Visualiza_NotaCredDesc.frm | 1495 | SELECT | DataConsDescRec.RecordSource = "select sum(importe) as SumaI… |
| Visualiza_NotaCredDesc.frm | 1673 | SELECT | rs_consDesc.Open "select sum(importe) as SumaImporte from De… |
| Visualiza_NotaCredDesc.frm | 1725 | UPDATE | ''        conn.Execute "UPDATE descuento_rec_nc SET utilizad… |
| CuentaCliente.frm | 1857 | SELECT | Visualiza_NotaCredDesc.DataDescRec.RecordSource = "select * … |
| CuentaCliente.frm | 2371 | SELECT | '        rs_descuento_rec_nc.Open "SELECT * FROM descuento_r… |
| trz_trazabilidad.frm | 6423 | SELECT | Visualiza_NotaCredDesc.DataDescRec.RecordSource = "select * … |
| trz_trazabilidad.frm | 7473 | SELECT | rs_descuento_rec_nc.Open "SELECT * FROM descuento_rec_nc WHE… |
| ConsultaComprobante.frm | 9470 | SELECT | rs_descuento_rec_nc.Open "SELECT * FROM descuento_rec_nc WHE… |
| ConsultaComprobante.frm | 11717 | SELECT | rs_descuento_rec_nc.Open "SELECT * FROM descuento_rec_nc WHE… |
| ReciboCobro.frm | 8000 | SELECT | rs_descuento_rec_nc.Open "SELECT * FROM descuento_rec_nc whe… |
| CargaComprobantesC.frm | 3173 | SELECT | DataDescRec.RecordSource = " Select * from descuento_rec_nc … |
| Visualiza_ReciboCobroC.frm | 7263 | SELECT | rs_descuento_rec_nc.Open "SELECT * FROM descuento_rec_nc whe… |
| Visualiza_ReciboCobroC.frm | 11720 | SELECT | '        NotaCredDesc.DataDescREC.RecordSource = "select * f… |
| Visualiza.bas | 3302 | SELECT | Visualiza_NotaCredDesc.DataDescRec.RecordSource = "select * … |
| Visualiza.bas | 6359 | SELECT | rs_descuento_rec_nc.Open "SELECT * FROM descuento_rec_nc WHE… |

---

## 4. Uso en Synap (reports)

*No se encontraron referencias en el módulo reports.*

[← Índice de tablas](../DB_INDICE_TABLAS.md)