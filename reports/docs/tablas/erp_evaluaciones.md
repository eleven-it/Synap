# Tabla `erp_evaluaciones`

Base: **administranet**

---

## 1. Schema (information_schema)

### 1.1 Columnas

| Campo | Tipo | Nulo | PK | FK | Referencia |
|-------|------|------|----|----|------------|
| id_evaluaciones | INT | No | ✓ |  |  |
| id_tipo_evaluacion | INT | Sí |  |  |  |
| id_sub_tipo_evaluacion | INT | Sí |  |  |  |
| id_proyecto | INT | Sí |  |  |  |
| id_cliente | INT | Sí |  |  |  |
| id_usuario_evaluador | INT | Sí |  |  |  |
| id_plantilla_evaluacion | INT | Sí |  |  |  |
| nro_evaluacion | VARCHAR | Sí |  |  |  |
| fecha | DATE | Sí |  |  |  |
| resultado_obtenido | VARCHAR | Sí |  |  |  |
| resultado_esperado | VARCHAR | Sí |  |  |  |
| estado | VARCHAR | Sí |  |  |  |
| fechaFin | TIMESTAMP | No |  |  |  |
| nro_ot | VARCHAR | Sí |  |  |  |
| aprobada | VARCHAR | Sí |  |  |  |
| ruta_adjunto | TEXT | Sí |  |  |  |
| anulado | VARCHAR | Sí |  |  |  |
| recorrido | VARCHAR | Sí |  |  |  |
| id_zona | INT | Sí |  |  |  |
| duracion | VARCHAR | Sí |  |  |  |
| motivo_anulacion | VARCHAR | Sí |  |  |  |
| comentario | TEXT | Sí |  |  |  |

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