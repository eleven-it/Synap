# Tabla `self_checkout_invoice`

Base: **administranet**

---

## 1. Schema (information_schema)

### 1.1 Columnas

| Campo | Tipo | Nulo | PK | FK | Referencia |
|-------|------|------|----|----|------------|
| id | BIGINT | No | ✓ |  |  |
| cart_id | BIGINT | No |  |  |  |
| codigo_movimiento | BIGINT | No |  |  |  |
| id_cuentacliente | BIGINT | No |  |  |  |
| nro_comprobante | VARCHAR | No |  |  |  |
| tipo_comprobante | VARCHAR | No |  |  |  |
| estado | VARCHAR | No |  |  |  |
| cae | VARCHAR | Sí |  |  |  |
| vto_cae | DATE | Sí |  |  |  |
| fe_regimen | VARCHAR | Sí |  |  |  |
| request_payload | TEXT | Sí |  |  |  |
| response_payload | TEXT | Sí |  |  |  |
| error_msg | VARCHAR | Sí |  |  |  |
| created_at | DATETIME | No |  |  |  |
| updated_at | DATETIME | No |  |  |  |

### 1.2 Relaciones (FK del catálogo)

*No hay claves foráneas definidas en el catálogo para esta tabla.*

---

## 2. Relaciones inferidas desde consultas SQL

Relaciones detectadas por uso en código (JOINs en VB6 y Synap). Sirven para diseñar una DB normalizada.

*No se encontraron JOINs que involucren esta tabla en el código escaneado.*

---

## 3. Uso en AdministraNET (VB6)

Formularios y procedimientos que referencian esta tabla (lectura/escritura). Base para migración AdministraNET → Synap.

*No se encontraron referencias a esta tabla en el código VB6 escaneado.*

---

## 4. Uso en Synap (reports)

*No se encontraron referencias en el módulo reports.*

[← Índice de tablas](../DB_INDICE_TABLAS.md)