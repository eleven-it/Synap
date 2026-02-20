# Tabla `chequetercero_temp_new`

Base: **administranet**

---

## 1. Schema (information_schema)

### 1.1 Columnas

| Campo | Tipo | Nulo | PK | FK | Referencia |
|-------|------|------|----|----|------------|
| Nrocheque | DECIMAL | Sí |  |  |  |
| CodBanco | INT | Sí |  |  |  |
| Librador | VARCHAR | Sí |  |  |  |
| CodCliente | INT | Sí |  |  |  |
| CodProveedor | INT | Sí |  |  |  |
| Importe | DECIMAL | Sí |  |  |  |
| FechaEmision | DATE | Sí |  |  |  |
| FechaCobro | DATE | Sí |  |  |  |
| FechaVto | DATE | Sí |  |  |  |
| NroChequera | VARCHAR | Sí |  |  |  |
| Anulado | VARCHAR | Sí |  |  |  |
| CUITLibrador | VARCHAR | Sí |  |  |  |
| Rechazado | CHAR | Sí |  |  |  |
| id_chequetercero_temp | DOUBLE | No | ✓ |  |  |
| CodUsuario | INT | No |  |  |  |
| CodigoMovimientoOP | DECIMAL | Sí |  |  |  |
| CodigoMovimientoREC | DECIMAL | Sí |  |  |  |
| id_caja_cheque | INT | Sí |  |  |  |
| visualiza | VARCHAR | Sí |  |  |  |
| codigo_movimiento_fact | DOUBLE | Sí |  |  |  |
| tipo_cheque | VARCHAR | Sí |  |  |  |
| id_cheque | BIGINT | Sí |  |  |  |
| NroCompREC | VARCHAR | Sí |  |  |  |

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