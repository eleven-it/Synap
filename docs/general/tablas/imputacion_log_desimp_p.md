# Tabla `imputacion_log_desimp_p`

Base: **administranet**

---

## 1. Schema (information_schema)

### 1.1 Columnas

| Campo | Tipo | Nulo | PK | FK | Referencia |
|-------|------|------|----|----|------------|
| id_log_desimp_p | BIGINT | No | ✓ |  |  |
| id_imputacion | BIGINT | Sí |  |  |  |
| id_proveedor | BIGINT | Sí |  |  |  |
| nro_fact_nd | VARCHAR | Sí |  |  |  |
| nro_op_nc | VARCHAR | Sí |  |  |  |
| id_usuario | BIGINT | Sí |  |  |  |
| fecha_control | TIMESTAMP | No |  |  |  |

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
| AsigPagoD.frm | 1058 | SELECT | rs_log_desimp.Open "SELECT * FROM imputacion_log_desimp_p WH… |

---

## 4. Uso en Synap (reports)

*No se encontraron referencias en el módulo reports.*

[← Índice de tablas](../DB_INDICE_TABLAS.md)