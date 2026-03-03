# Tabla `tc_cupones_temp`

Base: **administranet**

---

## 1. Schema (information_schema)

### 1.1 Columnas

| Campo | Tipo | Nulo | PK | FK | Referencia |
|-------|------|------|----|----|------------|
| id_cupones_temp | DOUBLE | No | ✓ |  |  |
| fecha | DATE | Sí |  |  |  |
| nro_comprobante | VARCHAR | Sí |  |  |  |
| moneda | CHAR | Sí |  |  |  |
| ingreso | DOUBLE | Sí |  |  |  |
| egreso | DOUBLE | Sí |  |  |  |
| saldo | DOUBLE | Sí |  |  |  |
| codigo_movimiento | DOUBLE | Sí |  |  |  |
| nombre_cliente | VARCHAR | Sí |  |  |  |
| detalle | MEDIUMTEXT | Sí |  |  |  |
| id_caja | DOUBLE | Sí |  |  |  |
| id_usuario | INT | Sí |  |  |  |
| id_tc_comprobante | DOUBLE | Sí |  |  |  |
| visualiza | VARCHAR | Sí |  |  |  |
| nro_lote_tc | VARCHAR | Sí |  |  |  |

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
| CargaLiquidacionTC.frm | 1960 | SELECT | DataTC.RecordSource = "select * from tc_cupones_temp  where … |
| CargaLiquidacionTC.frm | 1973 | SELECT | rs_Tcupones.Open "SELECT SUM(ingreso) as sumcup  from tc_cup… |
| CargaLiquidacionTC.frm | 1997 | SELECT | DataTC.RecordSource = "select * from tc_cupones_temp" |
| CargaLiquidacionTC.frm | 2290 | SELECT | conn.Execute "DELETE FROM tc_cupones_temp WHERE id_usuario =… |
| CargaLiquidacionTC.frm | 2290 | DELETE | conn.Execute "DELETE FROM tc_cupones_temp WHERE id_usuario =… |
| ListaCuponesTC.frm | 429 | SELECT | conn.Execute "DELETE tc_cupones_temp.* FROM tc_cupones_temp … |
| ListaCuponesTC.frm | 431 | INSERT | conn.Execute "INSERT INTO tc_cupones_temp( " & _ |
| ListaCuponesTC.frm | 454 | SELECT | rs_Tcupones.Open "SELECT SUM(ingreso) as sumcup  from tc_cup… |
| ListaCuponesTC.frm | 481 | SELECT | CargaLiquidacionTC.DataTC.RecordSource = "SELECT * FROM tc_c… |
| ListaCuponesTC.frm | 517 | SELECT | CargaLiquidacionTC.DataTC.RecordSource = "select * from tc_c… |
| ListaCuponesTC.frm | 526 | SELECT | CargaLiquidacionTC.DataTC.RecordSource = "select * from tc_c… |
| ListaCuponesTC.frm | 555 | SELECT | rs_Tcupones.Open "SELECT SUM(ingreso) as sumcup  from tc_cup… |
| ListaCuponesTC.frm | 584 | SELECT | CargaLiquidacionTC.DataTC.RecordSource = "select * from tc_c… |
| Principal.frm | 6099 | SELECT | conn.Execute "delete from tc_cupones_temp where id_usuario =… |
| Principal.frm | 6099 | DELETE | conn.Execute "delete from tc_cupones_temp where id_usuario =… |
| Principal.frm | 6165 | SELECT | conn.Execute "delete from tc_cupones_temp where id_usuario =… |
| Principal.frm | 6165 | DELETE | conn.Execute "delete from tc_cupones_temp where id_usuario =… |
| LibroBanco.frm | 4228 | SELECT | CargaLiquidacionTC.DataTC.RecordSource = "select * from tc_c… |
| LibroBanco.frm | 4254 | SELECT | CargaLiquidacionTC.DataTC.RecordSource = "select * from tc_c… |

---

## 4. Uso en Synap (reports)

*No se encontraron referencias en el módulo reports.*

[← Índice de tablas](../DB_INDICE_TABLAS.md)