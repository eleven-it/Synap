# Tabla `erp_ficha_personal`

Base: **administranet**

---

## 1. Schema (information_schema)

### 1.1 Columnas

| Campo | Tipo | Nulo | PK | FK | Referencia |
|-------|------|------|----|----|------------|
| id_ficha_personal | INT | No | ✓ |  |  |
| id_usuario | INT | Sí |  |  |  |
| nacionalidad | VARCHAR | Sí |  |  |  |
| grupo_sanguineo | VARCHAR | Sí |  |  |  |
| fecha_vto_conducir | DATE | Sí |  |  |  |
| fecha_vto_defensivo | DATE | Sí |  |  |  |
| licencia_conducir | VARCHAR | Sí |  |  |  |
| manejo_defensivo | VARCHAR | Sí |  |  |  |
| sindicato | VARCHAR | Sí |  |  |  |
| fecha_afiliacion | DATE | Sí |  |  |  |
| obra_social | VARCHAR | Sí |  |  |  |
| cuil | VARCHAR | Sí |  |  |  |
| estado_civil | VARCHAR | Sí |  |  |  |
| codbanco | INT | Sí |  |  |  |
| cbu | VARCHAR | Sí |  |  |  |
| fecha_ingreso | DATE | Sí |  |  |  |
| fecha_vto_examen_medico | DATE | Sí |  |  |  |
| tipo_licencia_conducir | VARCHAR | Sí |  |  |  |
| foto | LONGBLOB | Sí |  |  |  |
| llave_tacografo | VARCHAR | Sí |  |  |  |
| id_puesto | INT | Sí |  |  |  |
| anulado | VARCHAR | Sí |  |  |  |
| id_sue_abm_empleado | DOUBLE | Sí |  |  |  |

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
| Erp_ABM_FichaPersonal.frm | 449 | SELECT | '                                 " FROM erp_ficha_personal … |
| Erp_ABM_FichaPersonal.frm | 493 | SELECT | '                                 " FROM erp_ficha_personal … |
| ABMUsuarios.frm | 677 | JOIN | " LEFT JOIN erp_ficha_personal ON erp_ficha_personal.id_usua… |
| ABMUsuarios.frm | 944 | SELECT | rs_cons_ficha.Open "SELECT * FROM erp_ficha_personal WHERE i… |
| Erp_Carga_FichaPersonal.frm | 1360 | SELECT | rs_ficha_personal.Open "SELECT * FROM erp_ficha_personal WHE… |
| Erp_Carga_FichaPersonal.frm | 1428 | SELECT | rs_ficha_personal.Open "SELECT * FROM erp_ficha_personal WHE… |
| Erp_Carga_FichaPersonal.frm | 1515 | UPDATE | conn.Execute "UPDATE erp_ficha_personal SET erp_ficha_person… |
| Erp_Carga_FichaPersonal.frm | 1707 | SELECT | rs.Open "SELECT * FROM erp_ficha_personal WHERE id_usuario =… |

---

## 4. Uso en Synap (reports)

*No se encontraron referencias en el módulo reports.*

[← Índice de tablas](../DB_INDICE_TABLAS.md)