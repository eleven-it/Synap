# Tabla `menurapido_grupo`

Base: **administranet**

---

## 1. Schema (information_schema)

### 1.1 Columnas

| Campo | Tipo | Nulo | PK | FK | Referencia |
|-------|------|------|----|----|------------|
| id_menurapido_grupo | INT | No | ✓ |  |  |
| nombre_grupo | VARCHAR | Sí |  |  |  |
| id_puesto | INT | Sí |  |  |  |
| activo | INT | Sí |  |  |  |

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
| CargaPuesto.frm | 713 | SELECT | rs_permiso_menurapido.Open "SELECT * FROM menurapido_grupo w… |
| CargaPermiso_Sistema_Puesto.frm | 3545 | SELECT | Data_Grupo_Menu.RecordSource = "SELECT * FROM menurapido_gru… |
| Principal.frm | 2187 | SELECT | .Source = "SELECT * FROM menurapido_grupo WHERE id_puesto = … |
| Principal.frm | 2198 | SELECT | .Source = "SELECT * FROM menurapido_grupo WHERE id_puesto = … |
| Principal.frm | 2209 | SELECT | .Source = "SELECT * FROM menurapido_grupo WHERE id_puesto = … |
| Principal.frm | 2219 | SELECT | .Source = "SELECT * FROM menurapido_grupo WHERE id_puesto = … |
| Principal.frm | 2229 | SELECT | .Source = "SELECT * FROM menurapido_grupo WHERE id_puesto = … |
| Principal.frm | 2239 | SELECT | .Source = "SELECT * FROM menurapido_grupo WHERE id_puesto = … |
| Principal.frm | 2249 | SELECT | .Source = "SELECT * FROM menurapido_grupo WHERE id_puesto = … |
| Principal.frm | 2264 | SELECT | .Source = "SELECT * FROM menurapido_grupo WHERE id_puesto = … |
| Principal.frm | 2274 | SELECT | .Source = "SELECT * FROM menurapido_grupo WHERE id_puesto = … |
| Principal.frm | 2284 | SELECT | .Source = "SELECT * FROM menurapido_grupo WHERE id_puesto = … |
| Principal.frm | 2294 | SELECT | .Source = "SELECT * FROM menurapido_grupo WHERE id_puesto = … |
| Principal.frm | 2305 | SELECT | .Source = "SELECT * FROM menurapido_grupo WHERE id_puesto = … |
| Principal.frm | 2315 | SELECT | .Source = "SELECT * FROM menurapido_grupo WHERE id_puesto = … |
| Principal.frm | 2325 | SELECT | .Source = "SELECT * FROM menurapido_grupo WHERE id_puesto = … |
| Principal.frm | 2335 | SELECT | .Source = "SELECT * FROM menurapido_grupo WHERE id_puesto = … |
| Principal.frm | 2345 | SELECT | .Source = "SELECT * FROM menurapido_grupo WHERE id_puesto = … |
| Principal.frm | 2355 | SELECT | .Source = "SELECT * FROM menurapido_grupo WHERE id_puesto = … |
| Principal.frm | 2369 | SELECT | .Source = "SELECT * FROM menurapido_grupo WHERE id_puesto = … |
| Principal.frm | 2379 | SELECT | .Source = "SELECT * FROM menurapido_grupo WHERE id_puesto = … |
| Principal.frm | 2389 | SELECT | .Source = "SELECT * FROM menurapido_grupo WHERE id_puesto = … |
| Principal.frm | 2399 | SELECT | .Source = "SELECT * FROM menurapido_grupo WHERE id_puesto = … |
| Principal.frm | 2409 | SELECT | .Source = "SELECT * FROM menurapido_grupo WHERE id_puesto = … |
| Principal.frm | 2419 | SELECT | .Source = "SELECT * FROM menurapido_grupo WHERE id_puesto = … |
| Principal.frm | 2429 | SELECT | .Source = "SELECT * FROM menurapido_grupo WHERE id_puesto = … |
| Principal.frm | 2439 | SELECT | .Source = "SELECT * FROM menurapido_grupo WHERE id_puesto = … |
| Principal.frm | 2449 | SELECT | .Source = "SELECT * FROM menurapido_grupo WHERE id_puesto = … |
| Principal.frm | 2459 | SELECT | .Source = "SELECT * FROM menurapido_grupo WHERE id_puesto = … |
| Principal.frm | 2474 | SELECT | .Source = "SELECT * FROM menurapido_grupo WHERE id_puesto = … |
| Principal.frm | 2484 | SELECT | .Source = "SELECT * FROM menurapido_grupo WHERE id_puesto = … |
| Principal.frm | 2494 | SELECT | .Source = "SELECT * FROM menurapido_grupo WHERE id_puesto = … |
| Principal.frm | 2504 | SELECT | .Source = "SELECT * FROM menurapido_grupo WHERE id_puesto = … |
| Principal.frm | 2514 | SELECT | .Source = "SELECT * FROM menurapido_grupo WHERE id_puesto = … |
| CargaPermiso_Sistema.frm | 4663 | SELECT | Data_Grupo_Menu.RecordSource = "SELECT * FROM menurapido_gru… |

---

## 4. Uso en Synap (reports)

*No se encontraron referencias en el módulo reports.*

[← Índice de tablas](../DB_INDICE_TABLAS.md)