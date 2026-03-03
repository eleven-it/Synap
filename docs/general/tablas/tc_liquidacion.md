# Tabla `tc_liquidacion`

Base: **administranet**

---

## 1. Schema (information_schema)

### 1.1 Columnas

| Campo | Tipo | Nulo | PK | FK | Referencia |
|-------|------|------|----|----|------------|
| id_tc_liquidacion | DOUBLE | No | ✓ |  |  |
| id_cuentabancaria | DOUBLE | Sí |  |  |  |
| id_tc | DOUBLE | Sí |  |  |  |
| nro_tc_liquidacion | MEDIUMTEXT | Sí |  |  |  |
| neto_tc_liquidacion | DOUBLE | Sí |  |  |  |
| importe_tc_liquidacion | DOUBLE | Sí |  |  |  |
| id_caja | DOUBLE | Sí |  |  |  |
| comisiones_tc_liquidacion | DOUBLE | Sí |  |  |  |
| iva_comisiones_tc_liquidacion | DOUBLE | Sí |  |  |  |
| total_retencion_tc_liquidacion | DECIMAL | Sí |  |  |  |
| total_descuento_tc_liquidacion | DOUBLE | Sí |  |  |  |
| codigo_movimiento | DECIMAL | Sí |  |  |  |
| id_banco | DOUBLE | Sí |  |  |  |
| anulado | VARCHAR | Sí |  |  |  |

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
| Exportacion.frm | 884 | JOIN | "LEFT JOIN tc_liquidacion ON (tc_liquidacion.codigo_movimien… |
| Exportacion.frm | 960 | JOIN | "LEFT JOIN tc_liquidacion ON (tc_liquidacion.codigo_movimien… |
| Exportacion.frm | 6519 | JOIN | "LEFT JOIN tc_liquidacion ON (tc_liquidacion.id_tc = tarjeta… |
| Exportacion.frm | 6950 | JOIN | "LEFT JOIN tc_liquidacion ON (tc_liquidacion.id_tc = tarjeta… |
| CargaLiquidacionTC.frm | 1567 | SELECT | rs_tc_liquidacion.Open "SELECT * FROM tc_liquidacion where i… |
| LibroBanco.frm | 2374 | SELECT | rs_consulta_anul.Open "SELECT * from tc_liquidacion WHERE id… |
| LibroBanco.frm | 2396 | SELECT | rs_tc_liquidacion.Open "SELECT * from tc_liquidacion where i… |
| LibroBanco.frm | 2452 | SELECT | rs_consulta_caja.Open "SELECT * FROM tc_liquidacion WHERE id… |
| LibroBanco.frm | 4170 | SELECT | rs_tc_liquidacion.Open "SELECT * FROM tc_liquidacion where i… |

---

## 4. Uso en Synap (reports)

*No se encontraron referencias en el módulo reports.*

[← Índice de tablas](../DB_INDICE_TABLAS.md)