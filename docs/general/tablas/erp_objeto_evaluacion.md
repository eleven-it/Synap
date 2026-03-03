# Tabla `erp_objeto_evaluacion`

Base: **administranet**

---

## 1. Schema (information_schema)

### 1.1 Columnas

| Campo | Tipo | Nulo | PK | FK | Referencia |
|-------|------|------|----|----|------------|
| id_objeto_evaluacion | INT | No | ✓ |  |  |
| nombre_objeto_evaluacion | VARCHAR | Sí |  |  |  |
| id_cliente | INT | Sí |  |  |  |
| id_proveedor | INT | Sí |  |  |  |
| tipo | VARCHAR | Sí |  |  |  |
| id_usuario | INT | Sí |  |  |  |
| IDArt | INT | Sí |  |  |  |
| patron | VARCHAR | Sí |  |  |  |
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

*No se encontraron referencias a esta tabla en el código VB6 escaneado.*

---

## 4. Uso en Synap (reports)

*No se encontraron referencias en el módulo reports.*

[← Índice de tablas](../DB_INDICE_TABLAS.md)