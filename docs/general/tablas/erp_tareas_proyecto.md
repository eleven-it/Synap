# Tabla `erp_tareas_proyecto`

Base: **administranet**

---

## 1. Schema (information_schema)

### 1.1 Columnas

| Campo | Tipo | Nulo | PK | FK | Referencia |
|-------|------|------|----|----|------------|
| id_tareas_proyecto | INT | No | ✓ |  |  |
| id_proyecto | DECIMAL | Sí |  |  |  |
| id_tarea | DECIMAL | Sí |  |  |  |
| desde | DATE | Sí |  |  |  |
| hasta | DATE | Sí |  |  |  |
| cant_dias | DECIMAL | Sí |  |  |  |
| tipo_tarea | VARCHAR | Sí |  |  |  |
| orden_tarea | INT | Sí |  |  |  |
| estado_tarea | VARCHAR | Sí |  |  |  |
| anulado | VARCHAR | Sí |  |  |  |
| nombre_tarea | VARCHAR | Sí |  |  |  |

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
| Erp_Carga_Parte_Diario.frm | 3906 | SELECT | DataTarea.RecordSource = "SELECT * FROM erp_tareas_proyecto … |
| Erp_Planificacion_Tarea.frm | 964 | SELECT | rs_tarea_proyecto.Open "SELECT * FROM erp_tareas_proyecto WH… |
| Erp_Planificacion_Tarea.frm | 1197 | UPDATE | conn.Execute "UPDATE erp_tareas_proyecto SET anulado='Si' WH… |
| Erp_Planificacion_Tarea.frm | 1299 | SELECT | " FROM erp_tareas_proyecto " & _ |
| Visualiza_Erp_Carga_Parte_Diario.frm | 3483 | SELECT | DataTarea.RecordSource = "SELECT * FROM erp_tareas_proyecto … |

---

## 4. Uso en Synap (reports)

*No se encontraron referencias en el módulo reports.*

[← Índice de tablas](../DB_INDICE_TABLAS.md)