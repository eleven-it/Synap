# Tabla `caja_arqueo`

Base: **administranet**

---

## 1. Schema (information_schema)

### 1.1 Columnas

| Campo | Tipo | Nulo | PK | FK | Referencia |
|-------|------|------|----|----|------------|
| id_caja_arqueo | BIGINT | No | ✓ |  |  |
| id_caja_abm_origen | BIGINT | Sí |  |  |  |
| id_caja_abm_destino | BIGINT | Sí |  |  |  |
| cant_dinero_1 | DOUBLE | Sí |  |  |  |
| cant_dinero_2 | DOUBLE | Sí |  |  |  |
| cant_dinero_5 | DOUBLE | Sí |  |  |  |
| cant_dinero_10 | DOUBLE | Sí |  |  |  |
| cant_dinero_20 | DOUBLE | Sí |  |  |  |
| cant_dinero_50 | DOUBLE | Sí |  |  |  |
| cant_dinero_100 | DOUBLE | Sí |  |  |  |
| cant_dinero_200 | DOUBLE | Sí |  |  |  |
| cant_dinero_500 | DOUBLE | Sí |  |  |  |
| cant_dinero_1000 | DOUBLE | Sí |  |  |  |
| cant_dinero_2000 | DOUBLE | Sí |  |  |  |
| cant_dinero_5000 | DOUBLE | Sí |  |  |  |
| monto_dinero_1 | DOUBLE | Sí |  |  |  |
| monto_dinero_2 | DOUBLE | Sí |  |  |  |
| monto_dinero_5 | DOUBLE | Sí |  |  |  |
| monto_dinero_10 | DOUBLE | Sí |  |  |  |
| monto_dinero_20 | DOUBLE | Sí |  |  |  |
| monto_dinero_50 | DOUBLE | Sí |  |  |  |
| monto_dinero_100 | DOUBLE | Sí |  |  |  |
| monto_dinero_200 | DOUBLE | Sí |  |  |  |
| monto_dinero_500 | DOUBLE | Sí |  |  |  |
| monto_dinero_1000 | DOUBLE | Sí |  |  |  |
| monto_dinero_2000 | DOUBLE | Sí |  |  |  |
| monto_dinero_5000 | DOUBLE | Sí |  |  |  |
| codigo_movimiento | BIGINT | Sí |  |  |  |
| id_usuario | INT | Sí |  |  |  |
| anulado | VARCHAR | Sí |  |  |  |
| fecha_hora | DATETIME | Sí |  |  |  |
| id_vendedor | INT | Sí |  |  |  |
| cant_dinero_10000 | DOUBLE | Sí |  |  |  |
| cant_dinero_20000 | DOUBLE | Sí |  |  |  |
| monto_dinero_10000 | DOUBLE | Sí |  |  |  |
| monto_dinero_20000 | DECIMAL | Sí |  |  |  |
| id_cierre_efectivo | BIGINT | Sí |  |  |  |
| id_cierre_tarjeta | BIGINT | Sí |  |  |  |
| id_cierre_cheque | BIGINT | Sí |  |  |  |

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
| CargaMovCaja.frm | 2373 | SELECT | rs_caja_arqueo.Open "SELECT * FROM caja_arqueo WHERE id_caja… |
| Caja_Arqueo.frm | 1145 | SELECT | rs_caja_arqueo.Open "SELECT * FROM caja_arqueo WHERE codigo_… |
| Caja_Arqueo.frm | 1232 | SELECT | rs_caja_arqueo.Open "SELECT * FROM caja_arqueo WHERE codigo_… |
| Caja.frm | 1789 | SELECT | rs_caja_arqueo.Open "SELECT * FROM caja_arqueo WHERE codigo_… |

---

## 4. Uso en Synap (reports)

*No se encontraron referencias en el módulo reports.*

[← Índice de tablas](../DB_INDICE_TABLAS.md)