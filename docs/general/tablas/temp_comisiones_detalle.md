# Tabla `temp_comisiones_detalle`

Base: **administranet**

---

## 1. Schema (information_schema)

### 1.1 Columnas

| Campo | Tipo | Nulo | PK | FK | Referencia |
|-------|------|------|----|----|------------|
| id_temp | INT | No | ✓ |  |  |
| sesion_id | VARCHAR | No |  |  |  |
| FechaVenta | DATE | No |  |  |  |
| TipoComprobante | VARCHAR | No |  |  |  |
| NroComprobante | VARCHAR | No |  |  |  |
| CodViajante | INT | No |  |  |  |
| NombreViajante | VARCHAR | No |  |  |  |
| IDArt | INT | No |  |  |  |
| NombreArticulo | VARCHAR | No |  |  |  |
| CodigoMarca | INT | Sí |  |  |  |
| NombreMarca | VARCHAR | Sí |  |  |  |
| CodigoRubro | INT | Sí |  |  |  |
| NombreRubro | VARCHAR | Sí |  |  |  |
| CodigoSubRubro | INT | Sí |  |  |  |
| NombreSubRubro | VARCHAR | Sí |  |  |  |
| porcentaje | DECIMAL | No |  |  |  |
| tipo_comision | VARCHAR | No |  |  |  |
| tipo_calculo | VARCHAR | No |  |  |  |
| CantidadVendida | DECIMAL | No |  |  |  |
| MontoBase | DECIMAL | No |  |  |  |
| MontoNC | DECIMAL | Sí |  |  |  |
| MontoComision | DECIMAL | No |  |  |  |
| id_stock | BIGINT | No |  |  |  |

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