# Tabla `erp_recursos`

Base: **administranet**

---

## 1. Schema (information_schema)

### 1.1 Columnas

| Campo | Tipo | Nulo | PK | FK | Referencia |
|-------|------|------|----|----|------------|
| id_recurso | INT | No | ✓ |  |  |
| nombre_recurso | VARCHAR | Sí |  |  |  |
| tipo_recurso | VARCHAR | Sí |  |  |  |
| anulado | VARCHAR | Sí |  |  |  |
| id_unimed | INT | Sí |  |  |  |

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
| Erp_Carga_Costeo_Proyecto.frm | 565 | SELECT | DataRecurso.RecordSource = "SELECT id_recurso,nombre_recurso… |
| Erp_Carga_Parte_Diario.frm | 3882 | JOIN | " LEFT JOIN `erp_recursos` AS rec ON rec.`id_recurso` = pr.`… |
| ConsultaComprobante.frm | 13502 | JOIN | "LEFT JOIN erp_recursos AS er ON er.id_recurso = rp.`id_recu… |
| Visualiza_Erp_Carga_Parte_Diario.frm | 3459 | JOIN | " LEFT JOIN `erp_recursos` AS rec ON rec.`id_recurso` = pr.`… |
| Erp_Carga_Rercurso.frm | 469 | SELECT | rs_recursos.Open "SELECT * FROM erp_recursos WHERE nombre_re… |
| Erp_Carga_Rercurso.frm | 485 | SELECT | rs_recursos.Open "SELECT * FROM erp_recursos WHERE  id_recur… |
| Erp_Carga_Rercurso.frm | 505 | SELECT | Erp_ABM_Recursos.DataRecursos.RecordSource = "SELECT * FROM … |
| Erp_Carga_Rercurso.frm | 517 | SELECT | rs_recursos.Open "SELECT * FROM erp_recursos WHERE id_recurs… |
| Erp_Carga_Rercurso.frm | 535 | SELECT | Erp_ABM_Recursos.DataRecursos.RecordSource = "SELECT * FROM … |
| Erp_Costeo_Proyecto.frm | 1349 | SELECT | " FROM erp_recursos AS rec" & _ |
| Erp_Costeo_Proyecto.frm | 1386 | JOIN | " LEFT JOIN `erp_recursos` AS rec ON rec.`id_recurso` = pr.`… |
| Erp_ABM_Recursos.frm | 494 | SELECT | DataRecursos.RecordSource = "SELECT erp_recursos.*,unidmed.n… |
| Erp_ABM_Recursos.frm | 542 | SELECT | DataRecursos.RecordSource = "SELECT erp_recursos.*,unidmed.n… |
| Erp_ABM_Recursos.frm | 547 | SELECT | DataRecursos.RecordSource = "SELECT erp_recursos.*,unidmed.n… |
| Erp_Planificacion_Tareas.frm | 1290 | SELECT | DataRecurso.RecordSource = "SELECT id_recurso,nombre_recurso… |
| Erp_Planificacion_Tareas.frm | 1318 | JOIN | " LEFT JOIN `erp_recursos` AS rec ON rec.`id_recurso` = pr.`… |
| Visualiza.bas | 8602 | JOIN | "LEFT JOIN erp_recursos AS er ON er.id_recurso = rp.`id_recu… |
| Visualiza.bas | 8701 | JOIN | " LEFT JOIN `erp_recursos` AS rec ON rec.`id_recurso` = pr.`… |

---

## 4. Uso en Synap (reports)

*No se encontraron referencias en el módulo reports.*

[← Índice de tablas](../DB_INDICE_TABLAS.md)