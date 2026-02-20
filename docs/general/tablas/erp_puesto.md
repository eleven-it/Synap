# Tabla `erp_puesto`

Base: **administranet**

---

## 1. Schema (information_schema)

### 1.1 Columnas

| Campo | Tipo | Nulo | PK | FK | Referencia |
|-------|------|------|----|----|------------|
| id_puesto | DOUBLE | No | ✓ |  |  |
| nombre_puesto | VARCHAR | Sí |  |  |  |
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
| Erp_Carga_Cargo.frm | 240 | SELECT | rs_cargo.Open "SELECT * FROM erp_puesto WHERE nombre_puesto … |
| Erp_Carga_Cargo.frm | 256 | SELECT | rs_cargo.Open "SELECT * FROM erp_puesto WHERE id_puesto = 0"… |
| Erp_Carga_Cargo.frm | 271 | SELECT | Erp_ABM_Cargo.DataCargo.RecordSource = "SELECT * FROM erp_pu… |
| Erp_Carga_Cargo.frm | 282 | SELECT | rs_cargo.Open "SELECT * FROM erp_puesto WHERE id_puesto = " … |
| Erp_Carga_Cargo.frm | 295 | SELECT | Erp_ABM_Cargo.DataCargo.RecordSource = "SELECT * FROM erp_pu… |
| ABMUsuarios.frm | 678 | JOIN | " LEFT JOIN erp_puesto ON erp_puesto.id_puesto = erp_ficha_p… |
| ABMUsuarios.frm | 969 | SELECT | Erp_Carga_FichaPersonal.data_puesto.RecordSource = "SELECT *… |
| Erp_Carga_FichaPersonal.frm | 1328 | SELECT | data_puesto.RecordSource = "SELECT * FROM erp_puesto WHERE a… |
| Erp_ABM_Cargo.frm | 424 | SELECT | DataCargo.RecordSource = "SELECT * FROM erp_puesto WHERE nom… |
| Erp_ABM_Cargo.frm | 464 | SELECT | DataCargo.RecordSource = "SELECT * FROM erp_puesto ORDER BY … |

---

## 4. Uso en Synap (reports)

*No se encontraron referencias en el módulo reports.*

[← Índice de tablas](../DB_INDICE_TABLAS.md)