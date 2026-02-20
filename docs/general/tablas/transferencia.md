# Tabla `transferencia`

Base: **administranet**

---

## 1. Schema (information_schema)

### 1.1 Columnas

| Campo | Tipo | Nulo | PK | FK | Referencia |
|-------|------|------|----|----|------------|
| id_transf | BIGINT | No | ✓ |  |  |
| fecha_transf | DATE | Sí |  |  |  |
| nro_referencia | DOUBLE | Sí |  |  |  |
| id_cuentabancaria | INT | Sí |  |  |  |
| importe_transf | DOUBLE | Sí |  |  |  |
| tipo | VARCHAR | Sí |  |  |  |
| detalle_transf | VARCHAR | Sí |  |  |  |
| codigo_movimiento | BIGINT | Sí |  |  |  |
| anulado | VARCHAR | Sí |  |  |  |
| detalle_transf_global | MEDIUMTEXT | Sí |  |  |  |

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
| Visualiza_ReciboCobro.frm | 9452 | SELECT | '        data_transferencia.RecordSource = "SELECT transfere… |
| Visualiza_ReciboCobro.frm | 12822 | SELECT | rs_transferencia.Open "SELECT * FROM transferencia WHERE tra… |
| OrdenPago.frm | 7054 | SELECT | rs_transferencia.Open "SELECT * FROM transferencia where id_… |
| ConsultaComprobante.frm | 11837 | SELECT | rs_transferencia.Open "SELECT * FROM transferencia where cod… |
| ConsultaComprobante.frm | 12953 | SELECT | rs_transferencia.Open "SELECT * FROM transferencia where cod… |
| ConsultaComprobante.frm | 30867 | SELECT | '            rs_transferencia.Open "SELECT * FROM transferen… |
| ConsultaComprobante.frm | 30869 | SELECT | rs_transferencia.Open "SELECT transferencia.*, banco.Nombre … |
| ReciboCobro.frm | 6887 | SELECT | rs_transferencia.Open "SELECT * FROM transferencia where id_… |
| Visualiza_OrdenPago.frm | 9436 | SELECT | rs_transferencia.Open "SELECT * FROM transferencia WHERE tra… |
| Visualiza.bas | 6371 | SELECT | rs_transferencia.Open "SELECT transferencia.*, banco.Nombre … |
| Visualiza.bas | 7663 | SELECT | rs_transferencia.Open "SELECT transferencia.*, banco.Nombre … |
| Visualiza.bas | 20662 | SELECT | rs_transferencia.Open "SELECT transferencia.*, banco.Nombre … |
| Visualiza.bas | 21095 | SELECT | rs_transferencia.Open "SELECT transferencia.*, banco.Nombre … |

---

## 4. Uso en Synap (reports)

*No se encontraron referencias en el módulo reports.*

[← Índice de tablas](../DB_INDICE_TABLAS.md)