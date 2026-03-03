# Tabla `erp_recurso_proyecto_temp`

Base: **administranet**

---

## 1. Schema (information_schema)

### 1.1 Columnas

| Campo | Tipo | Nulo | PK | FK | Referencia |
|-------|------|------|----|----|------------|
| id_erp_proyecto_recurso_temp | INT | No | ✓ |  |  |
| id_recurso | INT | Sí |  |  |  |
| id_usuario | INT | Sí |  |  |  |
| coeficiente | DOUBLE | Sí |  |  |  |
| nombre_recurso | VARCHAR | Sí |  |  |  |
| tipo_recurso | VARCHAR | Sí |  |  |  |
| IdArt | INT | Sí |  |  |  |
| nombre_articulo | VARCHAR | Sí |  |  |  |
| id_proyecto | INT | Sí |  |  |  |
| id_recurso_proyecto | INT | Sí |  |  |  |
| nombre_unimed | VARCHAR | Sí |  |  |  |
| tipo_unidad | VARCHAR | Sí |  |  |  |

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
| Erp_Carga_Costeo_Proyecto.frm | 506 | SELECT | rs_recurso_proyecto_temp.Open "SELECT * FROM erp_recurso_pro… |
| Erp_Carga_Costeo_Proyecto.frm | 525 | SELECT | Erp_Costeo_Proyecto.DataRecursoTemp.RecordSource = "SELECT *… |
| Erp_Costeo_Proyecto.frm | 1127 | SELECT | rs_recurso_temp.Open "SELECT * FROM erp_recurso_proyecto_tem… |
| Erp_Costeo_Proyecto.frm | 1137 | SELECT | DataRecursoTemp.RecordSource = "SELECT * FROM erp_recurso_pr… |
| Erp_Costeo_Proyecto.frm | 1162 | SELECT | DataRecursoTemp.RecordSource = "SELECT * FROM erp_recurso_pr… |
| Erp_Costeo_Proyecto.frm | 1280 | SELECT | conn.Execute "DELETE FROM erp_recurso_proyecto_temp WHERE id… |
| Erp_Costeo_Proyecto.frm | 1280 | DELETE | conn.Execute "DELETE FROM erp_recurso_proyecto_temp WHERE id… |
| Erp_Costeo_Proyecto.frm | 1286 | SELECT | DataRecursoTemp.RecordSource = "SELECT * FROM erp_recurso_pr… |
| Erp_Costeo_Proyecto.frm | 1295 | SELECT | conn.Execute "DELETE FROM erp_recurso_proyecto_temp WHERE id… |
| Erp_Costeo_Proyecto.frm | 1295 | DELETE | conn.Execute "DELETE FROM erp_recurso_proyecto_temp WHERE id… |
| Erp_Costeo_Proyecto.frm | 1298 | SELECT | DataRecursoTemp.RecordSource = "SELECT * FROM erp_recurso_pr… |
| Erp_Costeo_Proyecto.frm | 1371 | SELECT | conn.Execute "DELETE FROM erp_recurso_proyecto_temp WHERE id… |
| Erp_Costeo_Proyecto.frm | 1371 | DELETE | conn.Execute "DELETE FROM erp_recurso_proyecto_temp WHERE id… |
| Erp_Costeo_Proyecto.frm | 1394 | SELECT | DataRecursoTemp.RecordSource = "SELECT * FROM erp_recurso_pr… |
| Erp_Costeo_Proyecto.frm | 1422 | SELECT | DataRecursoTemp.RecordSource = "SELECT * FROM erp_recurso_pr… |
| Erp_Costeo_Proyecto.frm | 1573 | SELECT | conn.Execute "DELETE FROM erp_recurso_proyecto_temp WHERE id… |
| Erp_Costeo_Proyecto.frm | 1573 | DELETE | conn.Execute "DELETE FROM erp_recurso_proyecto_temp WHERE id… |
| Erp_Planificacion_Tareas.frm | 1116 | SELECT | rs_recurso_temp.Open "SELECT * FROM erp_recurso_proyecto_tem… |
| Erp_Planificacion_Tareas.frm | 1126 | SELECT | DataRecursoTemp.RecordSource = "SELECT * FROM erp_recurso_pr… |
| Erp_Planificacion_Tareas.frm | 1148 | SELECT | DataRecursoTemp.RecordSource = "SELECT * FROM erp_recurso_pr… |
| Erp_Planificacion_Tareas.frm | 1233 | SELECT | conn.Execute "DELETE FROM erp_recurso_proyecto_temp WHERE id… |
| Erp_Planificacion_Tareas.frm | 1233 | DELETE | conn.Execute "DELETE FROM erp_recurso_proyecto_temp WHERE id… |
| Erp_Planificacion_Tareas.frm | 1239 | SELECT | DataRecursoTemp.RecordSource = "SELECT * FROM erp_recurso_pr… |
| Erp_Planificacion_Tareas.frm | 1248 | SELECT | conn.Execute "DELETE FROM erp_recurso_proyecto_temp WHERE id… |
| Erp_Planificacion_Tareas.frm | 1248 | DELETE | conn.Execute "DELETE FROM erp_recurso_proyecto_temp WHERE id… |
| Erp_Planificacion_Tareas.frm | 1251 | SELECT | DataRecursoTemp.RecordSource = "SELECT * FROM erp_recurso_pr… |
| Erp_Planificacion_Tareas.frm | 1325 | SELECT | DataRecursoTemp.RecordSource = "SELECT * FROM erp_recurso_pr… |
| Erp_Planificacion_Tareas.frm | 1347 | SELECT | DataRecursoTemp.RecordSource = "SELECT * FROM erp_recurso_pr… |
| Erp_Planificacion_Tareas.frm | 1497 | SELECT | conn.Execute "DELETE FROM erp_recurso_proyecto_temp WHERE id… |
| Erp_Planificacion_Tareas.frm | 1497 | DELETE | conn.Execute "DELETE FROM erp_recurso_proyecto_temp WHERE id… |
| Principal.frm | 6085 | SELECT | conn.Execute "delete from erp_recurso_proyecto_temp where id… |
| Principal.frm | 6085 | DELETE | conn.Execute "delete from erp_recurso_proyecto_temp where id… |
| Principal.frm | 6151 | SELECT | conn.Execute "delete from erp_recurso_proyecto_temp where id… |
| Principal.frm | 6151 | DELETE | conn.Execute "delete from erp_recurso_proyecto_temp where id… |

---

## 4. Uso en Synap (reports)

*No se encontraron referencias en el módulo reports.*

[← Índice de tablas](../DB_INDICE_TABLAS.md)