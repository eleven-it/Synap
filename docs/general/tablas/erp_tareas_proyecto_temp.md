# Tabla `erp_tareas_proyecto_temp`

Base: **administranet**

---

## 1. Schema (information_schema)

### 1.1 Columnas

| Campo | Tipo | Nulo | PK | FK | Referencia |
|-------|------|------|----|----|------------|
| id_erp_tarea_proyecto_temp | INT | No | ✓ |  |  |
| id_proyecto | INT | Sí |  |  |  |
| id_tarea | INT | Sí |  |  |  |
| desde | DATE | Sí |  |  |  |
| hasta | DATE | Sí |  |  |  |
| cant_dias | DECIMAL | Sí |  |  |  |
| tipo_tarea | VARCHAR | Sí |  |  |  |
| orden_tarea | INT | Sí |  |  |  |
| estado_tarea | VARCHAR | Sí |  |  |  |
| nombre_tarea | VARCHAR | Sí |  |  |  |
| anulado | VARCHAR | Sí |  |  |  |
| id_usuario | INT | Sí |  |  |  |
| id_tareas_proyecto | INT | Sí |  |  |  |

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
| Erp_Planificacion_Tarea.frm | 1060 | SELECT | rs_tarea_temp.Open "SELECT * FROM erp_tareas_proyecto_temp W… |
| Erp_Planificacion_Tarea.frm | 1071 | SELECT | Data_Tareas_Temp.RecordSource = "SELECT * FROM erp_tareas_pr… |
| Erp_Planificacion_Tarea.frm | 1099 | SELECT | Data_Tareas_Temp.RecordSource = "SELECT * FROM erp_tareas_pr… |
| Erp_Planificacion_Tarea.frm | 1195 | SELECT | conn.Execute "DELETE FROM erp_tareas_proyecto_temp WHERE id_… |
| Erp_Planificacion_Tarea.frm | 1195 | DELETE | conn.Execute "DELETE FROM erp_tareas_proyecto_temp WHERE id_… |
| Erp_Planificacion_Tarea.frm | 1201 | SELECT | Data_Tareas_Temp.RecordSource = "SELECT * FROM erp_tareas_pr… |
| Erp_Planificacion_Tarea.frm | 1210 | SELECT | conn.Execute "DELETE FROM erp_tareas_proyecto_temp WHERE id_… |
| Erp_Planificacion_Tarea.frm | 1210 | DELETE | conn.Execute "DELETE FROM erp_tareas_proyecto_temp WHERE id_… |
| Erp_Planificacion_Tarea.frm | 1213 | SELECT | Data_Tareas_Temp.RecordSource = "SELECT * FROM erp_tareas_pr… |
| Erp_Planificacion_Tarea.frm | 1306 | SELECT | Data_Tareas_Temp.RecordSource = "SELECT * FROM erp_tareas_pr… |
| Erp_Planificacion_Tarea.frm | 1423 | SELECT | conn.Execute "DELETE FROM erp_tareas_proyecto_temp WHERE id_… |
| Erp_Planificacion_Tarea.frm | 1423 | DELETE | conn.Execute "DELETE FROM erp_tareas_proyecto_temp WHERE id_… |
| Principal.frm | 6086 | SELECT | conn.Execute "delete from erp_tareas_proyecto_temp where id_… |
| Principal.frm | 6086 | DELETE | conn.Execute "delete from erp_tareas_proyecto_temp where id_… |
| Principal.frm | 6152 | SELECT | conn.Execute "delete from erp_tareas_proyecto_temp where id_… |
| Principal.frm | 6152 | DELETE | conn.Execute "delete from erp_tareas_proyecto_temp where id_… |

---

## 4. Uso en Synap (reports)

*No se encontraron referencias en el módulo reports.*

[← Índice de tablas](../DB_INDICE_TABLAS.md)