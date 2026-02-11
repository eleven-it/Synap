# Tabla `logi_abm_chofer`

Base: **administranet**

---

## 1. Schema (information_schema)

### 1.1 Columnas

| Campo | Tipo | Nulo | PK | FK | Referencia |
|-------|------|------|----|----|------------|
| id_chofer | DOUBLE | No | ✓ |  |  |
| nombre_chofer | VARCHAR | Sí |  |  |  |
| anulado | VARCHAR | Sí |  |  |  |
| CodigoProveedor | INT | Sí |  |  |  |
| tipo_documento | VARCHAR | Sí |  |  |  |
| documento_chofer | VARCHAR | Sí |  |  |  |
| id_usuario | INT | Sí |  |  |  |

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
| Logi_ABMRuta.frm | 575 | JOIN | "LEFT JOIN logi_abm_chofer ON (logi_abm_chofer.id_chofer = l… |
| Liq_ABM_Viajante.frm | 1008 | SELECT | data_chofer.RecordSource = "SELECT * FROM logi_abm_chofer WH… |
| Logi_CargaChofer.frm | 323 | SELECT | rs_chofe.Open "SELECT * FROM logi_abm_chofer WHERE nombre_ch… |
| Logi_CargaChofer.frm | 339 | SELECT | rs_chofe.Open "SELECT * FROM logi_abm_chofer WHERE id_chofer… |
| Logi_CargaChofer.frm | 355 | SELECT | Logi_ABMChofer.DataChofer.RecordSource = "SELECT * FROM logi… |
| Logi_CargaChofer.frm | 366 | SELECT | rs_chofe.Open "SELECT * FROM logi_abm_chofer WHERE id_chofer… |
| Logi_CargaChofer.frm | 381 | SELECT | Logi_ABMChofer.DataChofer.RecordSource = "SELECT * FROM logi… |
| Logi_ABMChofer.frm | 451 | SELECT | DataChofer.RecordSource = "SELECT * FROM logi_abm_chofer WHE… |
| Logi_ABMChofer.frm | 484 | SELECT | DataChofer.RecordSource = "SELECT * FROM logi_abm_chofer WHE… |
| Logi_CargaRuta.frm | 1751 | SELECT | "From logi_abm_chofer " & _ |
| Logi_CargaRuta.frm | 1782 | SELECT | "From logi_abm_chofer " & _ |
| Logi_CargaRuta.frm | 1873 | SELECT | "From logi_abm_chofer " & _ |
| Logi_CargaRuta.frm | 1905 | SELECT | "From logi_abm_chofer " & _ |
| Logi_CargaRuta.frm | 1966 | SELECT | data_chofer.RecordSource = "SELECT id_chofer, nombre_chofer … |
| Liq_Carga_Viajante.frm | 1015 | SELECT | data_chofer.RecordSource = "SELECT * FROM logi_abm_chofer WH… |

---

## 4. Uso en Synap (reports)

*No se encontraron referencias en el módulo reports.*

[← Índice de tablas](../DB_INDICE_TABLAS.md)