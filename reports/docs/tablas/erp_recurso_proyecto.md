# Tabla `erp_recurso_proyecto`

Base: **administranet**

---

## 1. Schema (information_schema)

### 1.1 Columnas

| Campo | Tipo | Nulo | PK | FK | Referencia |
|-------|------|------|----|----|------------|
| id_recurso_proyecto | INT | No | ✓ |  |  |
| id_articulo | INT | Sí |  |  |  |
| id_recurso | INT | Sí |  |  |  |
| coeficiente | DECIMAL | Sí |  |  |  |
| id_proyecto | INT | Sí |  |  |  |
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

| Archivo | Línea | Operación | Fragmento |
|---------|-------|-----------|-----------|
| Erp_Carga_Costeo_Proyecto.frm | 490 | SELECT | rs_recurso_proyecto.Open "SELECT * FROM erp_recurso_proyecto… |
| Erp_Carga_Parte_Diario.frm | 3395 | SELECT | '                                        "FROM erp_recurso_p… |
| Erp_Carga_Parte_Diario.frm | 3403 | SELECT | "FROM erp_recurso_proyecto AS rp " & _ |
| Erp_Carga_Parte_Diario.frm | 3523 | SELECT | " FROM erp_recurso_proyecto AS rp " & _ |
| Erp_Carga_Parte_Diario.frm | 3881 | SELECT | " FROM `erp_recurso_proyecto` AS pr" & _ |
| ConsultaComprobante.frm | 13501 | SELECT | "FROM erp_recurso_proyecto as rp " & _ |
| Visualiza_Erp_Carga_Parte_Diario.frm | 2994 | SELECT | '                                        "FROM erp_recurso_p… |
| Visualiza_Erp_Carga_Parte_Diario.frm | 3002 | SELECT | "FROM erp_recurso_proyecto AS rp " & _ |
| Visualiza_Erp_Carga_Parte_Diario.frm | 3124 | SELECT | " FROM erp_recurso_proyecto AS rp " & _ |
| Visualiza_Erp_Carga_Parte_Diario.frm | 3458 | SELECT | " FROM `erp_recurso_proyecto` AS pr" & _ |
| Erp_ABM_Proyecto.frm | 1246 | SELECT | rs_costeo.Open "SELECT * FROM erp_recurso_proyecto WHERE id_… |
| Erp_Busqueda_PD.frm | 1167 | JOIN | " LEFT JOIN `erp_recurso_proyecto` as cost ON(cost.`id_artic… |
| Erp_Busqueda_PD.frm | 1193 | JOIN | " LEFT JOIN `erp_recurso_proyecto` as cost ON(cost.`id_artic… |
| Erp_Costeo_Proyecto.frm | 1067 | SELECT | rs_recurso_proyecto.Open "SELECT * FROM erp_recurso_proyecto… |
| Erp_Costeo_Proyecto.frm | 1282 | UPDATE | conn.Execute "UPDATE erp_recurso_proyecto SET anulado='Si' W… |
| Erp_Costeo_Proyecto.frm | 1385 | SELECT | " FROM `erp_recurso_proyecto` AS pr" & _ |
| Erp_Planificacion_Tareas.frm | 1055 | SELECT | rs_recurso_proyecto.Open "SELECT * FROM erp_recurso_proyecto… |
| Erp_Planificacion_Tareas.frm | 1235 | UPDATE | conn.Execute "UPDATE erp_recurso_proyecto SET anulado='Si' W… |
| Erp_Planificacion_Tareas.frm | 1317 | SELECT | " FROM `erp_recurso_proyecto` AS pr" & _ |
| Visualiza.bas | 8601 | SELECT | "FROM erp_recurso_proyecto as rp " & _ |
| Visualiza.bas | 8700 | SELECT | " FROM `erp_recurso_proyecto` AS pr" & _ |

---

## 4. Uso en Synap (reports)

*No se encontraron referencias en el módulo reports.*

[← Índice de tablas](../DB_INDICE_TABLAS.md)