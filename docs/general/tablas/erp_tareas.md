# Tabla `erp_tareas`

Base: **administranet**

---

## 1. Schema (information_schema)

### 1.1 Columnas

| Campo | Tipo | Nulo | PK | FK | Referencia |
|-------|------|------|----|----|------------|
| id_tarea | INT | No | ✓ |  |  |
| nombre_tarea | VARCHAR | Sí |  |  |  |
| descripcion_tarea | TEXT | Sí |  |  |  |
| anulado | VARCHAR | Sí |  |  |  |
| facturable | VARCHAR | Sí |  |  |  |
| abreviada | VARCHAR | Sí |  |  |  |

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
| Erp_ABM_Tareas.frm | 470 | SELECT | DataTareas.RecordSource = "SELECT * FROM erp_tareas WHERE no… |
| Erp_ABM_Tareas.frm | 510 | SELECT | DataTareas.RecordSource = "SELECT * FROM erp_tareas ORDER BY… |
| Erp_Carga_Tarea.frm | 303 | SELECT | rs_tareas.Open "SELECT * FROM erp_tareas WHERE nombre_tarea … |
| Erp_Carga_Tarea.frm | 319 | SELECT | rs_tareas.Open "SELECT * FROM erp_tareas WHERE  id_tarea = 0… |
| Erp_Carga_Tarea.frm | 341 | SELECT | Erp_ABM_Tareas.DataTareas.RecordSource = "SELECT * FROM erp_… |
| Erp_Carga_Tarea.frm | 353 | SELECT | rs_tareas.Open "SELECT * FROM erp_tareas WHERE id_tarea = " … |
| Erp_Carga_Tarea.frm | 372 | SELECT | Erp_ABM_Tareas.DataTareas.RecordSource = "SELECT * FROM erp_… |
| Erp_Planificacion_Tarea.frm | 1273 | SELECT | DataTarea.RecordSource = "SELECT erp_tareas.* FROM erp_tarea… |
| ConsultaComprobante.frm | 3033 | JOIN | " LEFT JOIN  erp_tareas AS tr ON tr.`id_tarea` = pd.`id_tare… |
| ConsultaComprobante.frm | 3067 | JOIN | " LEFT JOIN  erp_tareas AS tr ON tr.`id_tarea` = pd.`id_tare… |
| Visualiza.bas | 8508 | JOIN | " LEFT JOIN  erp_tareas AS tr ON tr.`id_tarea` = pd.`id_tare… |
| Visualiza.bas | 8686 | SELECT | Visualiza_Erp_Carga_Parte_Diario.DataTarea.RecordSource = "S… |

---

## 4. Uso en Synap (reports)

*No se encontraron referencias en el módulo reports.*

[← Índice de tablas](../DB_INDICE_TABLAS.md)